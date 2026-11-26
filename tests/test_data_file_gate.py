"""F6.8: the gate rule that reads the four data files.

The rule lives in `sanity_checks.py` as `check_data_files`, so the gate that runs during a conversion
and the gate that runs during a test cannot disagree. The rule reads each file through the module that
owns the row shape, so no second shape rule appears, and it reads no `.tf` file, so no block rule reads
a data file.

The four records are the codebase root set. The rule data pair is a unit-set file, so the same findings read
it inside each unit directory its own rows name (Epic 9, rule 5), and the report's data count names the
records at the root plus the pair's data member inside those directories: the printed member is not a data
file, the way the site print is not. `tests/conftest.py` states the set the count names, so the modules that
read it state no second derivation.

Sections, one per finding:

1. The file set: the gate reads the `.tf` files plus the data files the table names, each through the
   module that owns its row shape, the report names both sets, and `CHECK_ORDER` puts the data rule after the
   block rules and before the round-trip cross-check, which is the rule that reads two sets, and then before
   the byte rules.
2. Finding 1: a data file that does not read as its declared rows, and a data file with no rows.
3. Finding 2: the fields `naming.py` decides must be stated as the rule states them.
4. Finding 3: the joins, through `directory`.
5. Finding 4: the order, read back through `reference_edges.order`.
6. Finding 5: the site record and its printed form, and the rule data pair inside the unit directory its
   own rows name (Epic 9, rule 5).
7. Finding 6: the row ordinal, the truth across the corpus, determinism, and the exit code.
8. The codebase set for a run that writes into a codebase another run wrote (`docs/MULTI_RUN_CODEBASE.md` §5
   rule 2): the record set at the root is read as the merged set, so the rule reads rows for units the run did
   not build and compares the printed form inside a directory the run did not write.

Every test runs offline. The planted rows are built through the modules, so the tests state no second
shape rule either.
"""

import json
import shutil
import subprocess
from pathlib import Path

import codebase_state
import entry_coverage
import naming
import ownership
import reference_edges
import rule_data
import sanity_checks
import site_data
import unit_manifest
import write_path
from conftest import (
    CODEBASE_FIXTURE,
    FIXTURES_DIR,
    MODE_VALUES,
    RULE_TYPES,
    RUN_FIXTURE,
    SAMPLE_CONFIG,
    corpus_fixtures,
    data_file_set,
    partial_run,
    record_rows,
    run_script,
    write_merged_records,
    written_bytes,
)

CONVERTER = "panorama_to_terraform.py"
KITCHEN = "kitchen_sink.xml"

# The fixtures the corpus pins read: the read rule's accepted set, not a name rule. A fixture the rule refuses
# writes no file, so the gate never sees it (tests/test_robustness.py pins that path).
FIXTURES = corpus_fixtures()

# A unit the manifest names, and a unit only the ownership record names: the declared parent source
# case (F5.4), which the join rule allows.
SHARED = ("", "", "", "", "")
CHILD = ("Child-DG", "", "", "", "")
PARENT = ("Parent-DG", "", "", "", "")
SITE_VALUE = "Site Value"


def _run(source: Path, out_dir: Path) -> subprocess.CompletedProcess:
    """Run the converter as a script and return the process result."""
    return run_script(CONVERTER, str(source), "--output-dir", str(out_dir))


def _manifest_row(facts: tuple, rank: int = 1, after: tuple = ()) -> dict:
    """A manifest row as the rules state it, so only the field a test changes can be a finding."""
    row = dict(dict.fromkeys(unit_manifest.FIELD_ORDER, ""))
    row.update(dict(zip(unit_manifest.FACT_KEYS, facts, strict=True)))
    row["unit"] = unit_manifest.unit_name(facts)
    row["directory"] = unit_manifest.directory_name(facts, naming.sanitize)
    row["entry_count"] = 1
    row["references"] = []
    row["rank"] = rank
    row["after"] = list(after)
    return row


def _ownership_row(facts: tuple, entry: str, kind: str, owner_facts: tuple) -> dict:
    """An ownership row as the rules state it, with the owner named through its own facts."""
    row = dict(dict.fromkeys(ownership.FIELD_ORDER, ""))
    row.update(dict(zip(ownership.FACT_KEYS, facts, strict=True)))
    row["type"] = "panos_address"
    row["entry"] = entry
    row["source"] = "data_file_gate.xml"
    row["directory"] = unit_manifest.directory_name(facts, naming.sanitize)
    row["owner"] = unit_manifest.directory_name(owner_facts, naming.sanitize)
    row["kind"] = kind
    row["override"] = "unknown"
    return row


def _edge_row(referrer: str, target: str, entry: str) -> dict:
    """An edge row as the rules state it."""
    return dict(dict.fromkeys(reference_edges.FIELD_ORDER, "")) | {
        "referrer": referrer,
        "target": target,
        "type": "panos_address",
        "entry": entry,
    }


def _site_row(facts: tuple, value: str) -> dict:
    """A site row as the rules state it, with the variable name the mapping result states."""
    return {
        "directory": unit_manifest.directory_name(facts, naming.sanitize),
        "variables": {naming.variable_name(value): value},
    }


def _clean(facts_list: list, ownership_rows: list = (), edge_rows: list = ()) -> list:
    """Manifest rows as the tool writes them: identity order, with the two order fields filled by the
    order rule, so only the field a test changes can be a finding.
    """
    rows = sorted(
        [_manifest_row(facts) for facts in facts_list],
        key=lambda row: tuple(row[key] for key in unit_manifest.FACT_KEYS),
    )
    return reference_edges.order(rows, list(ownership_rows), list(edge_rows))


def _write(out_dir: Path, name: str, module, rows: list) -> list:
    """Write one record as its module renders it, through the write path, and return the rule findings.

    A record is a codebase root-set file, so the test writes it with the same builder the tool uses
    (F6.10.3, `docs/CODEBASE_ASSEMBLY.md` §14).
    """
    write_path.write_file(write_path.root_path(out_dir, name), module.render(rows))
    return sanity_checks.check_data_files(out_dir)


def _for_file(findings: list, name: str) -> list:
    """The findings for one file, so a test reads only the finding its own rule states."""
    return [finding for finding in findings if finding.file == name]


def _rule_row(facts: tuple, entry: str, resource: str) -> dict:
    """One rule row as the module that owns the row shape builds it, so this test states no second shape rule.

    The recorded object is what `rule_data.build_rows` reads the properties through, so the row is built by the
    rule that names the fields, and the key and the digest are the ones the identity rules produce.
    """
    recorded = dict(zip(unit_manifest.FACT_KEYS, facts, strict=True))
    recorded["name"] = entry
    # A field the matrix row names for the rule type, so the row holds a value the print rule can print.
    recorded[entry_coverage.MATRIX_BY_RESOURCE[resource]["properties"][0]] = "block"
    return rule_data.build_rows(resource, [recorded], naming.sanitize)[0]


def _write_pair(out_dir: Path, rows: list, resource: str, facts: list) -> list:
    """Write the rule data pair inside the unit directory its own rows name, through the write path (F6.10.3,
    `docs/CODEBASE_ASSEMBLY.md` §14), and return the data rule's findings.

    The manifest is planted first, through the module that owns the unit rule, so the join reads the unit set the
    pair joins to and only the pair can be a finding. The facts are the ones the rows were built from, so this
    helper states no unit rule of its own, and the directory written into is the one the first row names.
    """
    write_path.write_file(
        write_path.root_path(out_dir, unit_manifest.MANIFEST_FILE), unit_manifest.render(_clean(facts))
    )
    directory = rows[0]["directory"]
    write_path.write_file(
        write_path.unit_path(out_dir, directory, rule_data.data_file(resource)), rule_data.render(rows)
    )
    write_path.write_file(
        write_path.unit_path(out_dir, directory, rule_data.printed_file(resource)), rule_data.render_csv(rows)
    )
    return sanity_checks.check_data_files(out_dir)


# --- 1. The file set -----------------------------------------------------------


def test_the_gate_reads_the_tf_files_and_the_data_files_the_table_names(tmp_path):
    """The block rules read the `.tf` files; the data rule reads the data files the table names, each through
    the module that owns its row shape, so no second shape rule appears.

    Both counts are read as the derivation: the `.tf` count is the set the reader read, and the data count is the
    rows `sanity_checks.DATA_FILES` names that the run wrote plus the rule data pair's data member inside each unit
    directory its own rows name, read through `conftest.data_file_set`. Measured 2026-11-19: the table names 4 root
    rows and the sample run writes 2 of them (the manifest and the ownership record), and the pair is written inside
    one unit directory for 2 rule types, so the count is 4.
    """
    assert dict(sanity_checks.DATA_FILES) == {
        unit_manifest.MANIFEST_FILE: unit_manifest,
        ownership.OWNERSHIP_FILE: ownership,
        reference_edges.EDGE_FILE: reference_edges,
        site_data.SITE_DATA_FILE: site_data,
    }
    assert _run(SAMPLE_CONFIG, tmp_path).returncode == 0
    tf_files = sanity_checks.read_tf_files(tmp_path)
    assert tf_files and all(name.endswith(".tf") for name in tf_files), "the block reader is .tf-only"
    report = sanity_checks.run_checks(tmp_path)
    assert report.file_count == len(tf_files)
    written = data_file_set(tmp_path)
    assert report.data_file_count == len(written), (report.data_file_count, sorted(written))
    assert not report.failed, report.render()


def test_the_data_rule_reads_a_merged_record_through_the_same_reader(tmp_path):
    """The table stays the only data rule over the four records, and the reader it names reads a record that holds
    rows from two runs the same way: the rows the rule reads back are the merged rows, and the rule reports nothing
    for a codebase that holds rows from two committed runs.

    Measured 2026-11-22 on the committed material, with the rows read through each module's `parse_rows` and merged
    through `codebase_state.merge_rows`: the kitchen-sink run is the codebase, `address_objects.xml` is the second
    run, and the merged records are written through the write path into a copy of the first run's output. No finding,
    and the count names the same four root records. The order half agrees here because the second run names no edge
    row, so the order over a merged set is not what this pin measures; that half is piece 11B.3.
    """
    codebase_dir, run_dir = tmp_path / "codebase", tmp_path / "run"
    assert _run(FIXTURES_DIR / KITCHEN, codebase_dir).returncode == 0
    assert _run(FIXTURES_DIR / "address_objects.xml", run_dir).returncode == 0
    merged_dir = tmp_path / "merged"
    shutil.copytree(codebase_dir, merged_dir)
    merged = {}
    for name, module in sanity_checks.DATA_FILES:
        record = [entry for entry in codebase_state.JOIN_KEYS if entry[0] is module][0]
        run_file = run_dir / name
        run_rows = module.parse_rows(run_file.read_text(encoding="utf-8")) if run_file.is_file() else []
        codebase_rows = module.parse_rows((codebase_dir / name).read_text(encoding="utf-8"))
        rows = codebase_state.merge_rows(record, codebase_rows, run_rows)
        merged[module] = rows
        assert module.parse_rows(module.render(rows)) == rows, module.__name__
        _write(merged_dir, name, module, rows)
    findings = sanity_checks.check_data_files(merged_dir)
    assert findings == [], ", ".join(f.render() for f in findings)
    written = data_file_set(merged_dir)
    assert sanity_checks.count_data_files(merged_dir) == len(written), sorted(written)
    assert len(written) == 8, sorted(written)


def test_the_report_names_both_file_sets(tmp_path):
    """The report line and the console summary name the two sets, so a reader can tell which files the
    gate read.

    Both counts are read as the derivation: the `.tf` count is the set the reader read below the root, and the
    data count is the rows `sanity_checks.DATA_FILES` names that the run wrote plus the rule data pair's data
    member inside each unit directory its own rows name, read through `conftest.data_file_set`. Measured
    2026-11-19: the sample run — two units, so two sets — reads 14 `.tf` files and 4 data files, the manifest, the
    ownership record, and the pair inside one unit directory for 2 rule types; the kitchen-sink run writes all four
    root rows and the pair for 4 rule types, so it reads 8 data files. The resource count is 17 for the sample run,
    measured 2026-11-19 on the iterated rule block, one block per rule type per unit.
    """
    assert _run(SAMPLE_CONFIG, tmp_path).returncode == 0
    report = sanity_checks.run_checks(tmp_path)
    files = sanity_checks.read_tf_files(tmp_path)
    written = data_file_set(tmp_path)
    assert report.file_count == len(files), "the count names the unit set"
    assert report.data_file_count == len(written), (report.data_file_count, sorted(written))
    assert f"Files checked: {len(files)} .tf files, {len(written)} data files." in report.render(), report.render()
    assert (
        f"Sanity gate: PASS (0 FAIL, 0 WARN) - {len(files)} .tf files, {len(written)} data files, 17 resources"
    ) in report.console_summary(), report.console_summary()
    assert all(Path(name).parent.name for name in files), "the reader read the unit directories"

    # The printed form is not one of the four, so the count names only the records.
    kitchen = tmp_path / "kitchen"
    assert _run(FIXTURES_DIR / KITCHEN, kitchen).returncode == 0
    kitchen_rows = [name for name, _shape in sanity_checks.DATA_FILES if (kitchen / name).is_file()]
    assert len(kitchen_rows) == len(sanity_checks.DATA_FILES), sorted(kitchen_rows)
    assert sanity_checks.run_checks(kitchen).data_file_count == len(data_file_set(kitchen))
    assert sanity_checks.count_data_files(kitchen) == len(data_file_set(kitchen))
    # The pair's printed member is not a data file, the way the site print is not, so the count names only the
    # data member: measured on the same run, the derivation names 4 root records and 4 data members.
    printed = sorted(
        str(path.relative_to(kitchen))
        for resource in RULE_TYPES
        for path in kitchen.rglob(rule_data.printed_file(resource))
        if path.parent != kitchen
    )
    assert len(printed) == len(kitchen_rows), printed
    assert not any(name in data_file_set(kitchen) for name in printed), "the count names no printed member"


def test_check_order_puts_the_data_rule_after_the_block_rules(tmp_path):
    """The block rules, then the run-level text rules, then the data rule, then the two rules that read two
    sets, then the byte rules, then the two rules that run an external command. `tests/test_round_trip.py` and
    `tests/test_sanity_gate.py` pin why the two agreement rules sit together, and the plan check stays last
    because it is the command check that reads a directory rather than the files it wrote.

    `rule_blocks` is the last block rule, because it is the block rule that also reads the row set the data rule
    reads: it reads the `.tf` files through the one block reader, so it stays in the block-rule group, and the block
    it reads is the printed form of those rows.
    """
    assert sanity_checks.CHECK_ORDER == (
        "emitted_types",
        "location_present",
        "data_blocks",
        "import_blocks",
        "scope_blocks",
        "actions",
        "protocol_object",
        "filter_blocks",
        "certificate_blocks",
        "rule_blocks",
        "references",
        "variables",
        "data_files",
        "round_trip",
        "request_set",
        "control_chars",
        "placeholders",
        "tflint",
        "terraform",
    )
    assert _run(SAMPLE_CONFIG, tmp_path).returncode == 0
    report = sanity_checks.run_checks(tmp_path)
    assert [result.check for result in report.checks] == list(sanity_checks.CHECK_ORDER)


def test_no_block_rule_reads_a_data_file_and_the_data_rule_reads_no_tf_file():
    """Each rule reads one file set. The data rule takes the output directory and reads the records
    through their modules, so the module states no second shape rule.
    """
    source = Path(sanity_checks.__file__).read_text(encoding="utf-8")
    rule = source[source.index("def check_data_files") : source.index("def check_round_trip")]
    assert "read_tf_files" not in rule and "glob('*.tf')" not in rule, "the data rule reads no .tf file"
    assert "parse_rows" in rule, "the rule reads each row shape through its module"
    # The shape rule for a data file belongs to the module that wrote it, so the data rule holds none of its own.
    # The gate holds one shape rule, and it is the answer of the command it runs, not a file it wrote: measured by
    # `tests/test_sanity_gate.py::test_the_tflint_rule_set_is_data_in_the_gate`.
    assert "json" not in rule, "the data rule states no shape rule"
    assert "def check_data_files(output_dir: Path)" in source
    # The slice boundary is the cross-check, the rule that reads two sets, so the data rule reads no ledger.
    assert "ledger" not in rule, "the data rule reads no ledger, and the cross-check reads no record"
    # `rule_blocks` is the block rule that also reads the row set, so it reads the `.tf` files through the one block
    # reader and the rows through `rule_data`, the module that owns the row shape, and states no shape rule of its own.
    block_rule = source[source.index("def check_rule_blocks") : source.index("def check_references")]
    assert "blocks(" in block_rule, "the block rule reads the .tf files through the one block reader"
    assert "rule_data.parse_rows" in block_rule, "the block rule reads the row set through its module"
    assert "json" not in block_rule, "the block rule states no shape rule"


# --- 2. Finding 1: the row shape -----------------------------------------------


def test_a_data_file_that_does_not_read_as_its_rows_is_reported(tmp_path):
    """A refusal is a finding, not a crash: a data file a person hand-wrote is an input the gate reads."""
    assert _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, [_manifest_row(SHARED)]) == []
    (tmp_path / unit_manifest.MANIFEST_FILE).write_text('{"unit": "Shared"}', encoding="utf-8")
    findings = sanity_checks.check_data_files(tmp_path)
    assert [f.file for f in findings] == [unit_manifest.MANIFEST_FILE]
    assert findings[0].line == 0 and findings[0].severity == sanity_checks.FAIL
    assert "not a list of rows" in findings[0].detail, findings[0].render()

    broken = {"unit": "Shared", "directory": unit_manifest.directory_name(SHARED, naming.sanitize)}
    (tmp_path / unit_manifest.MANIFEST_FILE).write_text("[" + json.dumps(broken) + "]", encoding="utf-8")
    findings = sanity_checks.check_data_files(tmp_path)
    assert "does not state its fields" in findings[0].detail, findings[0].render()


def test_a_mode_that_is_not_a_value_of_the_pair_is_a_finding_through_the_reader(tmp_path):
    """Decision 2 (`docs/IMPORT_BINDING.md` §2, taken 2026-11-25): the gate reads the mode through
    `unit_manifest.parse_rows`, so a mode outside the pair reaches the rule as its finding 1, and the rule states no
    value set of its own. A row that states a value of the pair, and the answer for a unit the run did not mark,
    reads as no finding.

    Measured 2026-11-25 on a record written through `render` and read back through `parse_rows`, so the pin reads
    the rule's answer for the file and not the wording of the decision.
    """
    row = _manifest_row(SHARED)
    assert row["mode"] == unit_manifest.EMPTY_ANSWER, row
    assert _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, [row]) == []
    for value in MODE_VALUES:
        assert _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, [dict(row, mode=value)]) == []
    findings = _for_file(
        _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, [dict(row, mode="bound")]),
        unit_manifest.MANIFEST_FILE,
    )
    assert len(findings) == 1, [f.render() for f in findings]
    assert "value of the pair" in findings[0].detail, findings[0].render()
    assert findings[0].severity == sanity_checks.FAIL
    # The rule reads the row through its module, so the value set stays in the pair's owner and the gate names
    # no value and no field of its own.
    source = Path(sanity_checks.__file__).read_text(encoding="utf-8")
    rule = source[source.index("def check_data_files") : source.index("def check_round_trip")]
    assert "mode" not in rule, "the data rule states no value set and no field name of its own"


def test_a_data_file_with_no_rows_is_a_finding(tmp_path):
    """The content rule says a data file is written only when it has content, so a file that holds no
    rows cannot be in the output.
    """
    for name, module in sanity_checks.DATA_FILES:
        findings = _for_file(_write(tmp_path, name, module, []), name)
        assert len(findings) == 1, findings
        assert findings[0].line == 0
        assert "cannot hold no rows" in findings[0].detail, findings[0].render()


def test_a_data_file_the_run_did_not_write_is_not_a_finding(tmp_path):
    """A run writes a data file only when it has content, so an absent record is not a violation."""
    assert _run(SAMPLE_CONFIG, tmp_path).returncode == 0
    assert not (tmp_path / reference_edges.EDGE_FILE).is_file()
    assert not (tmp_path / site_data.SITE_DATA_FILE).is_file()
    assert sanity_checks.check_data_files(tmp_path) == []


# --- 3. Finding 2: the fields naming.py decides --------------------------------


def test_the_manifest_fields_naming_decides_must_be_stated_as_the_rule_states_them(tmp_path):
    """`unit` is the level name of the facts, and `directory` is the naming shape of the facts."""
    row = _manifest_row(CHILD)
    assert _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, [row]) == []
    planted = dict(row)
    planted["unit"] = "Child"
    planted["directory"] = "child_dg_deadbeef"
    findings = _for_file(
        _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, [planted]), unit_manifest.MANIFEST_FILE
    )
    assert len(findings) == 2, [f.render() for f in findings]
    assert any("level rule" in f.detail for f in findings)
    assert any("naming rule shape" in f.detail for f in findings)
    # The site record variable name is refused by `parse_rows`, so the rule states no second naming rule.
    # The clean manifest is written back first, so the join reads the same unit the naming rule states.
    _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, [row])
    bad_site = {"directory": row["directory"], "variables": {"site_value_x": SITE_VALUE}}
    findings = _for_file(_write(tmp_path, site_data.SITE_DATA_FILE, site_data, [bad_site]), site_data.SITE_DATA_FILE)
    assert len(findings) == 1 and "shape of its value" in findings[0].detail, findings
    assert all(f.file == site_data.SITE_DATA_FILE for f in findings)


def test_the_ownership_directory_must_be_the_shape_of_its_facts(tmp_path):
    """The record joins to the manifest on `directory`, so the field is the naming shape, not a free name."""
    row = _ownership_row(CHILD, "web", "declared", CHILD)
    assert _write(tmp_path, ownership.OWNERSHIP_FILE, ownership, [row]) == []
    planted = dict(row)
    planted["directory"] = "other_unit_deadbeef"
    planted["owner"] = planted["directory"]
    findings = _for_file(_write(tmp_path, ownership.OWNERSHIP_FILE, ownership, [planted]), ownership.OWNERSHIP_FILE)
    assert len(findings) == 1, [f.render() for f in findings]
    assert "naming rule shape" in findings[0].detail


# --- 4. Finding 3: the joins ---------------------------------------------------


def test_a_join_to_a_unit_the_manifest_does_not_name_is_a_finding(tmp_path):
    """The manifest is the file that states the units, so every other record joins to it on `directory`."""
    child = _manifest_row(CHILD)
    assert _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, [child]) == []
    outside = "outside_unit_deadbeef"
    site_row = {"directory": outside, "variables": {"site_value": SITE_VALUE}}
    findings = _for_file(_write(tmp_path, site_data.SITE_DATA_FILE, site_data, [site_row]), site_data.SITE_DATA_FILE)
    assert len(findings) == 1 and "names no unit the manifest names" in findings[0].detail, findings

    edge = _edge_row(outside, child["directory"], "web")
    findings = _write(tmp_path, reference_edges.EDGE_FILE, reference_edges, [edge])
    edge_findings = _for_file(findings, reference_edges.EDGE_FILE)
    assert len(edge_findings) == 2, [f.render() for f in edge_findings]
    assert any("referrer" in f.detail for f in edge_findings)
    assert any("joins no ownership row" in f.detail for f in edge_findings)


def test_the_parent_source_case_joins_to_the_ownership_record(tmp_path):
    """The tool writes an ownership row for an entry from a declared parent source, and the manifest
    names no unit for it (F5.4), so a join to a record directory is not a finding.
    """
    child = _manifest_row(CHILD)
    parent_row = _ownership_row(PARENT, "web", "definition", PARENT)
    override = _ownership_row(CHILD, "web", "override", PARENT)
    findings = _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, [child])
    findings += _write(tmp_path, ownership.OWNERSHIP_FILE, ownership, [parent_row, override])
    assert findings == [], [f.render() for f in findings]
    edge = _edge_row(child["directory"], parent_row["directory"], "web")
    assert _write(tmp_path, reference_edges.EDGE_FILE, reference_edges, [edge]) == []


def test_an_edge_row_must_join_to_an_ownership_row_that_names_the_target(tmp_path):
    """The join is the F6.2 rule on (`type`, `entry`): the owner of that row is the edge target."""
    declaring = _ownership_row(CHILD, "web", "declared", CHILD)
    edge = _edge_row(
        unit_manifest.directory_name(SHARED, naming.sanitize),
        unit_manifest.directory_name(CHILD, naming.sanitize),
        "web",
    )
    manifest = _clean([SHARED, CHILD], [declaring], [edge])
    _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, manifest)
    _write(tmp_path, ownership.OWNERSHIP_FILE, ownership, [declaring])
    assert _write(tmp_path, reference_edges.EDGE_FILE, reference_edges, [edge]) == []
    # A row whose target names a manifest unit but not the owner of the name is still a finding.
    planted = _edge_row(edge["referrer"], edge["target"], "other_entry")
    findings = _for_file(
        _write(tmp_path, reference_edges.EDGE_FILE, reference_edges, [planted]), reference_edges.EDGE_FILE
    )
    assert len(findings) == 1, [f.render() for f in findings]
    assert "joins no ownership row" in findings[0].detail, findings[0].render()
    assert findings[0].line == 1


def test_an_ambiguous_row_cannot_name_an_owner(tmp_path):
    """A `kind` `ambiguous` row states no owner, so a row that names one contradicts its kind."""
    assert _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, [_manifest_row(CHILD)]) == []
    row = _ownership_row(CHILD, "web", "ambiguous", CHILD)
    findings = _for_file(_write(tmp_path, ownership.OWNERSHIP_FILE, ownership, [row]), ownership.OWNERSHIP_FILE)
    assert len(findings) == 1 and "states no owner" in findings[0].detail, findings
    # The same row with no owner reads clean, because `ambiguous` is the case the rule cannot decide.
    clean = dict(row)
    clean["owner"] = ""
    assert _for_file(_write(tmp_path, ownership.OWNERSHIP_FILE, ownership, [clean]), ownership.OWNERSHIP_FILE) == []
    assert sanity_checks.check_data_files(tmp_path) == []


# --- 5. Finding 4: the order ---------------------------------------------------


def test_the_manifest_order_must_be_what_the_order_rule_produces(tmp_path):
    """`rank` and `after` are data the rule produces, so a row that states a different order is a finding."""
    filled = reference_edges.order([_manifest_row(CHILD)], [], [])[0]
    assert filled["rank"] == 1 and filled["after"] == []
    assert _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, [filled]) == []
    planted = dict(filled)
    planted["rank"] = 2
    planted["after"] = [unit_manifest.directory_name(SHARED, naming.sanitize)]
    findings = _for_file(
        _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, [planted]), unit_manifest.MANIFEST_FILE
    )
    assert len(findings) == 1, [f.render() for f in findings]
    assert "the order rule produces" in findings[0].detail, findings[0].render()


def test_after_names_only_units_the_manifest_names(tmp_path):
    """Rule 7 guard, read back through the data: an override whose owner is a parent-source unit adds no
    dependency, so `after` cannot name a directory the manifest does not state.
    """
    child = _manifest_row(CHILD)
    parent_directory = unit_manifest.directory_name(PARENT, naming.sanitize)
    parent_row = _ownership_row(PARENT, "web", "definition", PARENT)
    override = _ownership_row(CHILD, "web", "override", PARENT)
    filled = reference_edges.order([child], [parent_row, override], [])[0]
    assert filled["after"] == [], "the order graph reads only manifest units"
    planted = dict(filled)
    planted["after"] = [parent_directory]
    findings = _for_file(
        _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, [planted]), unit_manifest.MANIFEST_FILE
    )
    assert len(findings) == 1, [f.render() for f in findings]
    assert findings[0].line == 1


# --- 6. Finding 5: the printed form --------------------------------------------


def test_the_printed_form_must_be_the_record_rendered_by_its_rule(tmp_path):
    """`site.auto.tfvars` is the site record printed, so a file that is not the print is a finding."""
    assert _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, [_manifest_row(SHARED)]) == []
    row = _site_row(SHARED, SITE_VALUE)
    findings = _for_file(_write(tmp_path, site_data.SITE_DATA_FILE, site_data, [row]), site_data.SITE_DATA_FILE)
    assert findings == [], findings  # the shape and the join read clean
    # F6.10.3 (§14): the printed form is the unit's file, so the rule reads the file the row names and the
    # finding names the path from the codebase root.
    printed = write_path.unit_path(tmp_path, row["directory"], site_data.TFVARS_FILE)
    path = str(printed.relative_to(tmp_path))
    findings = sanity_checks.check_data_files(tmp_path)
    assert len(findings) == 1, "the printed form is missing"
    assert findings[0].file == path, findings[0].render()
    assert "must hold its printed form" in findings[0].detail, findings[0].render()

    write_path.write_file(printed, site_data.render_tfvars([row]))
    assert sanity_checks.check_data_files(tmp_path) == []
    write_path.write_file(printed, site_data.render_tfvars([row]) + 'site_value = "other"\n')
    findings = sanity_checks.check_data_files(tmp_path)
    assert len(findings) == 1 and "not the row rendered by the rule" in findings[0].detail, findings
    assert findings[0].file == path, findings[0].render()
    assert findings[0].line == 1, "the position is the row ordinal the record states"


def test_the_record_and_its_printed_form_stand_or_fall_together(tmp_path):
    """The content rule writes both or neither, so a printed form with no record is a finding."""
    # F6.10.3 (§14): the rule reads the record, then the printed form of each row inside the directory that
    # row names, so a row and its printed form stand together, and a printed form no row names is not a
    # finding: the data rule reads no file inside a unit directory by itself.
    rows = _clean([SHARED, CHILD])
    assert _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, rows) == []
    assert sanity_checks.check_data_files(tmp_path) == [], "the record has no row, so nothing is printed"
    site_rows = [_site_row(facts, "x") for facts in (SHARED, CHILD)]
    assert _write(tmp_path, site_data.SITE_DATA_FILE, site_data, site_rows)
    for row in site_rows:
        assert sanity_checks.check_data_files(tmp_path), f"row {row['directory']}: the unit must hold its form"
    for row in site_rows:
        write_path.write_file(
            write_path.unit_path(tmp_path, row["directory"], site_data.TFVARS_FILE), site_data.render_tfvars([row])
        )
    assert sanity_checks.check_data_files(tmp_path) == [], "the record and its printed forms read clean"
    unclaimed = tmp_path / "unit_no_row_names"
    write_path.write_file(unclaimed / site_data.TFVARS_FILE, site_data.TFVARS_HEADER + 'site_value = "x"\n')
    assert sanity_checks.check_data_files(tmp_path) == [], "the rule reads no file inside a unit directory"

    # Two rows that state one name with two values cannot print one line, so the print rule refuses. F6.10.3
    # (§14): a unit's file prints that unit's row, so one file never holds two rows, and the gate reads the
    # refusal only through the row it is comparing. The refusal is still the rule's decision, so the test
    # measures it through the rule, not through a printed file the run cannot write.
    site_rows = [
        {"directory": unit_manifest.directory_name(SHARED, naming.sanitize), "variables": {"site_list": ["a"]}},
        {"directory": unit_manifest.directory_name(CHILD, naming.sanitize), "variables": {"site_list": ["b"]}},
    ]
    try:
        site_data.render_tfvars(site_rows)
    except ValueError as exc:
        assert "states two values" in str(exc), exc
    else:
        raise AssertionError("the print rule must refuse two values for one name")
    findings = _for_file(_write(tmp_path, site_data.SITE_DATA_FILE, site_data, site_rows), site_data.SITE_DATA_FILE)
    assert findings == [], "one file prints one row, so the gate reads no conflict"


def test_the_rule_data_pair_is_read_inside_the_unit_directory_its_rows_name(tmp_path):
    """The pair is a unit-set file, so the data rule reads it inside each unit directory its own rows name
    (Epic 9, rule 5), and both members are named through `rule_data`, the module that owns the row shape.

    Both names come from the module, so this pin states no file name of its own; the pair reads clean when the
    directory it is in names the unit its rows name. The printed member is not a data file, so the count names only
    the data member: measured 2026-11-19 on the sample run, 2 records at the root plus the data member for 2 rule
    types inside the unit its rows name, so 4.
    """
    row = _rule_row(SHARED, "Rule-1", "panos_security_policy_rules")
    resource = "panos_security_policy_rules"
    findings = _write_pair(tmp_path, [row], resource, [SHARED])
    assert findings == [], findings
    names = {rule_data.data_file(resource), rule_data.printed_file(resource)}
    assert len(names) == 2, "the pair is two files, so a pair cannot name one file twice"
    members = sorted(p for p in tmp_path.rglob("*") if p.is_file() and p.name in names)
    assert len(members) == 2, sorted(p.name for p in members)
    assert all(p.parent != tmp_path for p in members), "the pair is read inside the unit directory its rows name"
    counted = set(data_file_set(tmp_path))
    data_member = f"{row['directory']}/{rule_data.data_file(resource)}"
    assert counted == {unit_manifest.MANIFEST_FILE, data_member}, sorted(counted)


def test_a_pair_member_at_the_codebase_root_names_no_unit(tmp_path):
    """The four records are the codebase root set and the pair is the unit set, so a member found at the root
    joins to no unit and is a whole-file finding, stated at row 0.
    """
    resource = "panos_security_policy_rules"
    row = _rule_row(SHARED, "Rule-1", resource)
    assert _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, _clean([SHARED])) == []
    for name in (rule_data.data_file(resource), rule_data.printed_file(resource)):
        write_path.write_file(write_path.root_path(tmp_path, name), rule_data.render([row]))
    findings = sanity_checks.check_data_files(tmp_path)
    whole = [f for f in findings if f.line == 0]
    assert len(findings) == 2 and len(whole) == 2, [f.render() for f in findings]
    assert all("names no unit" in f.detail for f in findings), [f.render() for f in findings]
    assert all(Path(f.file).parent.name == "" for f in findings), "a root member names no directory"
    assert len(data_file_set(tmp_path)) == 1, sorted(data_file_set(tmp_path))


def test_a_pair_member_inside_a_directory_no_row_names_is_a_finding(tmp_path):
    """The join reads the unit set through the manifest, so a pair inside a directory no manifest row names is a
    finding, and a pair inside the directory its own rows name reads clean.
    """
    resource = "panos_security_policy_rules"
    row = _rule_row(SHARED, "Rule-1", resource)
    assert _write_pair(tmp_path, [row], resource, [SHARED]) == []
    moved = tmp_path / "unit_no_row_names"
    moved.mkdir()
    for name in (rule_data.data_file(resource), rule_data.printed_file(resource)):
        (tmp_path / row["directory"] / name).rename(moved / name)
    findings = sanity_checks.check_data_files(tmp_path)
    whole = [f for f in findings if f.line == 0]
    assert len(findings) == 2 and len(whole) == 2, [f.render() for f in findings]
    assert all(f.severity == sanity_checks.FAIL for f in findings), "each finding is the data rule's FAIL"
    assert all(f.file.startswith("unit_no_row_names/") for f in findings), [f.render() for f in findings]
    assert len(data_file_set(tmp_path)) == 1, sorted(data_file_set(tmp_path))


def test_the_pair_members_stand_or_fall_together(tmp_path):
    """The content rule writes a data file only when it has content, so the pair's two members stand or fall
    together the way the site record and its printed form do: each member alone is a whole-file finding.
    """
    resource = "panos_security_policy_rules"
    row = _rule_row(SHARED, "Rule-1", resource)
    assert _write_pair(tmp_path, [row], resource, [SHARED]) == []
    directory = row["directory"]
    data_member = tmp_path / directory / rule_data.data_file(resource)
    printed_member = tmp_path / directory / rule_data.printed_file(resource)

    printed_member.unlink()
    findings = sanity_checks.check_data_files(tmp_path)
    assert len(findings) == 1 and "stand or fall together" in findings[0].detail, [f.render() for f in findings]
    assert findings[0].file == f"{directory}/{rule_data.printed_file(resource)}", findings[0].render()
    # The printed member enters no count, so a pair missing its printed member is still one data file.
    assert len(data_file_set(tmp_path)) == 2, sorted(data_file_set(tmp_path))

    printed_member.write_text(rule_data.render_csv([row]), encoding="utf-8")
    data_member.unlink()
    findings = sanity_checks.check_data_files(tmp_path)
    assert len(findings) == 1 and "stand or fall together" in findings[0].detail, [f.render() for f in findings]
    assert len(data_file_set(tmp_path)) == 1, sorted(data_file_set(tmp_path))


def test_the_printed_member_must_be_the_rows_rendered_by_its_rule(tmp_path):
    """Finding 5 for the pair: the printed member must equal `rule_data.render_csv` of the same rows, so the pair
    is one row set in two forms rather than two shapes.
    """
    resource = "panos_security_policy_rules"
    row = _rule_row(SHARED, "Rule-1", resource)
    assert _write_pair(tmp_path, [row], resource, [SHARED]) == []
    printed = tmp_path / row["directory"] / rule_data.printed_file(resource)
    printed.write_text("entry\nRule-1\n", encoding="utf-8")
    findings = sanity_checks.check_data_files(tmp_path)
    assert len(findings) == 1 and "is not the rows rendered by the rule that prints them" in findings[0].detail, [
        f.render() for f in findings
    ]
    assert findings[0].file == f"{row['directory']}/{rule_data.printed_file(resource)}", findings[0].render()


def test_a_pair_row_that_names_another_unit_is_a_finding_at_its_row_ordinal(tmp_path):
    """Finding 3 and finding 6 for the pair: the row's `directory` must name the unit the file it is in names, and
    the finding is stated at the row ordinal because a data row spans many lines.
    """
    resource = "panos_security_policy_rules"
    row = _rule_row(SHARED, "Rule-1", resource)
    # The second row is built from another unit's facts, so it reads as its own shape and names a different unit
    # than the file it is in.
    other = _rule_row(CHILD, "Rule-2", resource)
    findings = _write_pair(tmp_path, [row, other], resource, [SHARED])
    assert len(findings) == 1, [f.render() for f in findings]
    assert findings[0].line == 2, findings[0].render()
    assert findings[0].file == f"{row['directory']}/{rule_data.data_file(resource)}", findings[0].render()
    assert "is not the unit the file it is in names" in findings[0].detail, findings[0].render()


# --- 7. Finding 6: the position, the corpus, determinism, the exit code ---------


def test_a_data_file_finding_is_stated_at_its_row_ordinal(tmp_path):
    """A data row spans many lines, so the position is the row ordinal, and a whole-file finding states
    no row.
    """
    first, second = _manifest_row(("Datacenter-FW", "", "", "", "")), _manifest_row(("Office-FW", "", "", "", ""))
    filled = reference_edges.order([first, second], [], [])
    planted = dict(filled[1])
    planted["unit"] = "Office"
    findings = _write(tmp_path, unit_manifest.MANIFEST_FILE, unit_manifest, [filled[0], planted])
    assert len(findings) == 1, [f.render() for f in findings]
    assert findings[0].line == 2, findings[0].render()
    assert findings[0].render().startswith(f"{unit_manifest.MANIFEST_FILE}:2  ")
    whole = sanity_checks.Finding("data_files", sanity_checks.FAIL, unit_manifest.MANIFEST_FILE, 0, "x")
    assert whole.render().startswith(f"{unit_manifest.MANIFEST_FILE}  ")
    # The row ordinal is the identity order the file prints in.
    assert [tuple(row[key] for key in unit_manifest.FACT_KEYS) for row in filled] == [
        tuple(first[key] for key in unit_manifest.FACT_KEYS),
        tuple(second[key] for key in unit_manifest.FACT_KEYS),
    ]


def test_the_rule_reports_no_finding_on_the_files_the_tool_writes_for_every_fixture(tmp_path):
    """The tool writes the data through the same rules the gate reads, so a clean run has no finding."""
    for fixture in FIXTURES:
        out = tmp_path / fixture
        assert _run(FIXTURES_DIR / fixture, out).returncode == 0, fixture
        findings = sanity_checks.check_data_files(out)
        assert findings == [], f"{fixture}: " + ", ".join(f.render() for f in findings)
        # A record the run has no content for is not written, so the rule reads nothing for it, and the
        # report the conversion wrote counts the same files the test gate counts.
        report = sanity_checks.run_checks(out)
        assert report.data_file_count == len(data_file_set(out)), (fixture, sorted(data_file_set(out)))
        assert f"{report.data_file_count} data files" in report.render(), fixture


def test_the_rule_is_the_same_between_two_runs(tmp_path):
    """Two runs on the same source write the same bytes and report the same findings."""
    source = FIXTURES_DIR / KITCHEN
    first, second = tmp_path / "first", tmp_path / "second"
    assert _run(source, first).returncode == 0 and _run(source, second).returncode == 0
    # F6.10.3 (§14): the layout is the root set plus one directory per unit, so the two runs are
    # compared on the whole shape the run wrote.
    assert written_bytes(first) == written_bytes(second), "the same bytes write the same layout"
    for name, _ in sanity_checks.DATA_FILES:
        left, right = first / name, second / name
        if left.is_file():
            assert left.read_bytes() == right.read_bytes(), name
    assert sanity_checks.check_data_files(first) == sanity_checks.check_data_files(second)
    # The count is read as the derivation from the table's rows present in the output plus the pair's data member
    # inside each unit directory its own rows name, so a run that wrote a different set answers differently.
    # Measured 2026-11-19 on the kitchen-sink run: all 4 root rows are written, and the pair is written inside one
    # unit directory for 4 rule types, so the count is 8.
    written = data_file_set(first)
    assert sanity_checks.count_data_files(first) == len(written), (written,)
    assert sanity_checks.count_data_files(second) == len(written), (written,)


def test_a_data_file_finding_exits_non_zero(tmp_path):
    """The gate decides the exit code, and a data-file finding is a FAIL (the F4.1 rule)."""
    # The sample run writes no site record, so a planted empty record is not overwritten.
    (tmp_path / site_data.SITE_DATA_FILE).write_text("[]\n", encoding="utf-8")
    result = _run(SAMPLE_CONFIG, tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "SITE_DATA.json  a data file is written only when it has content" in result.stdout


# --- 8. The codebase set, for a run that writes into an existing codebase -------


def test_the_data_rule_reads_the_merged_record_as_the_codebase_set(tmp_path):
    """8.1 (`docs/MULTI_RUN_CODEBASE.md` §5 rule 2): for a run that writes into a codebase another run wrote, the
    record set at the root is the merged set, so the rule reads rows for units the run did not build and compares the
    printed form inside a directory the run did not write. The rule reads the row shape through each module's
    `parse_rows` and the merge through `codebase_state.merge_rows`, so it states no second shape rule and no merge of
    its own; the pattern and the merged record are read through `tests/conftest.py`.

    Measured 2026-11-22 on the committed pair: the kitchen-sink run is the codebase (11 units) and
    `address_objects.xml` is the second run (1 unit, `shared_45ca31c3`). Against the record the second run wrote at
    the root, the rule reports 37 findings: 29 on two records at the root (`REFERENCE_EDGES.json` 26,
    `SITE_DATA.json` 3), each naming a unit the record names no row for, while the manifest and ownership records
    read as their rows and state no finding, and 8 on the rule data pair inside
    `production_dg_6ce3cc69`, which names no unit the record names. Against the merged record, written at the root
    through `codebase_state.merge_rows` and `write_path`, the same tree reports no finding, including the printed
    form inside the 10 directories the second run did not write, and the count names the same 8 data files.
    """
    codebase, partial, run = partial_run(CODEBASE_FIXTURE, RUN_FIXTURE, tmp_path)
    findings = sanity_checks.check_data_files(partial)
    assert len(findings) == 37, [f.render() for f in findings]
    root = [f for f in findings if not Path(f.file).parent.name]
    assert len(root) == 29, [f.render() for f in root]
    assert len([f for f in root if Path(f.file).name == reference_edges.EDGE_FILE]) == 26, [f.render() for f in root]
    assert len([f for f in root if Path(f.file).name == site_data.SITE_DATA_FILE]) == 3, [f.render() for f in root]
    assert len([f for f in findings if Path(f.file).parent.name == "production_dg_6ce3cc69"]) == 8, [
        f.render() for f in findings
    ]
    assert all(f.severity == sanity_checks.FAIL for f in findings), "each finding is the data rule's FAIL"

    merged = tmp_path / "merged"
    shutil.copytree(partial, merged)
    write_merged_records(codebase, partial, merged)
    clean = sanity_checks.check_data_files(merged)
    assert clean == [], [f.render() for f in clean]
    written = data_file_set(merged)
    assert sanity_checks.count_data_files(merged) == len(written) == 8, sorted(written)
    # The printed form is the half that reads a directory the run did not write: the merged set names 11 units,
    # the run wrote 1, and each site row's printed form inside its own directory reads as the row renders.
    site_rows = record_rows(merged)[site_data]
    assert len(site_rows) == 3, sorted(row["directory"] for row in site_rows)
    assert all(
        write_path.unit_path(merged, row["directory"], site_data.TFVARS_FILE).read_text(encoding="utf-8")
        == site_data.render_tfvars([row])
        for row in site_rows
    ), "the printed form inside a directory the run did not write reads as the row renders it"
