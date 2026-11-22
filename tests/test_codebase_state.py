"""Epic 11 piece 11B.1: the merge rule in `codebase_state.py`.

One pin per fact the module states (`docs/MULTI_RUN_CODEBASE.md` §3 rules 1, 2, 3, 4 and 5), and the pins that read
the row shape through the module that owns it:

1. The join key per record, read through each record module's `parse_rows`: the manifest on `directory`, the
   ownership record on (`type`, `entry`) with the facts read through `state_coverage.ownership_key`, the edge
   record on the pair of entry identities, the site record on `directory`.
2. The merge rule: the run's rows replace the codebase's rows for the rows the run built, and the rows for the
   units the run did not build stay as the record states them. The merge names no unit set of its own: both sets
   are read through `unit_manifest.units`, the one unit rule.
3. The byte rule between two runs: a record with no existing file writes the bytes a single run writes today, so no
   committed golden changes.
4. The merge holds no run field, and the order of a merged set is read through each record's own order rule, not
   through which side a row came from.
5. The module states no rule an owner states and writes no file, so the `src/` scans read it clean.

Every pin runs offline and is grounded on committed material: the codebase's rows are the rows a run wrote for
`tests/fixtures/kitchen_sink.xml`, and the run's rows are the rows a run wrote for
`tests/fixtures/address_objects.xml`, each read back through its own module's `parse_rows`. No pin builds a row by
hand. The four cases the byte rule pin reads are the four cases the golden set names.
"""

import ast
from pathlib import Path

import codebase_state
import naming
import ownership
import reference_edges
import sanity_checks
import site_data
import state_coverage
import unit_manifest
from conftest import EXAMPLES_DIR, FIXTURES_DIR, JOIN_RECORDS, SRC_DIR, run_records

CONVERTER = "panorama_to_terraform.py"
# The committed material the pins read: the codebase, and a second run that names one unit inside it.
CODEBASE_FIXTURE = "kitchen_sink.xml"
RUN_FIXTURE = "address_objects.xml"
# The four cases the golden set names, so the byte rule is read on the same committed material the goldens read.
GOLDEN_CASES = (CODEBASE_FIXTURE, RUN_FIXTURE, "filter_containers.xml", "sample_panorama_config.xml")

# The join key per record, read through the table the module states, and the four records read through the data
# rule that owns the set, so this test module states no set of its own; both are read through `tests/conftest.py`.
DATA_RULE = tuple(sanity_checks.DATA_FILES)
SHAPES = {
    unit_manifest: unit_manifest.FIELD_ORDER,
    ownership: ownership.FIELD_ORDER,
    reference_edges: reference_edges.FIELD_ORDER,
    site_data: site_data.SITE_ROW_FIELDS,
}


def _case_path(case: str) -> Path:
    """The committed file a case names: the corpus, or the sample input the root index names."""
    path = FIXTURES_DIR / case
    return path if path.is_file() else EXAMPLES_DIR / case


def _rows(case: str, out: Path) -> dict:
    """Run the converter on committed material and return the rows each record module reads back.

    The run and the read-back are `tests/conftest.py`'s `run_records`, the one place the test set states the
    read-back, so a pin reads the record the run wrote and never a row it built.
    """
    return run_records(CONVERTER, _case_path(case), out)


def _merged(module, codebase_rows: list, run_rows: list) -> list:
    return codebase_state.merge_rows(JOIN_RECORDS[module], codebase_rows, run_rows)


# --- 1. The join key per record ------------------------------------------------


def test_the_join_key_for_the_manifest_record_is_the_unit_identity_read_as_directory(tmp_path):
    """The manifest row joins on `directory`, and that field is the §5 shape of the five scope facts, so the join key
    is the unit identity and the module states no second naming rule.
    """
    rows = _rows(CODEBASE_FIXTURE, tmp_path)[unit_manifest]
    assert rows, "the pin reads a record with content"
    for row in rows:
        key = codebase_state.join_key(JOIN_RECORDS[unit_manifest], row)
        # A key is a tuple of the fields it is built from, so the single-field key is the unit identity as the §5
        # naming rule shapes it.
        assert key == (unit_manifest.directory_name(unit_manifest.facts_of(row), naming.sanitize),), row
    keys = [codebase_state.join_key(JOIN_RECORDS[unit_manifest], row) for row in rows]
    assert len(set(keys)) == len(keys), "one key names one row"
    assert JOIN_RECORDS[unit_manifest][2] == "the unit identity", "the table names the fact the key joins on"
    assert JOIN_RECORDS[unit_manifest][1] == ("directory",), "the key is the field the record states"


def test_the_join_key_for_the_ownership_record_is_the_entry_identity_read_through_state_coverage(tmp_path):
    """The ownership row joins on (`type`, `entry`) with the facts, which is `state_coverage.ownership_key`, the one
    identity key rule, so `codebase_state.py` builds no key of its own.

    Measured 2026-11-22 on the accepted corpus: the key is unique for every row of every fixture, so `source` is not
    what keeps two rows apart on the committed material, and the record's order rule, `ownership.row_key`, is this
    key with the source the row names.
    """
    rows = _rows(CODEBASE_FIXTURE, tmp_path)[ownership]
    assert rows, "the pin reads a record with content"
    record = JOIN_RECORDS[ownership]
    assert record[4] is state_coverage.ownership_key, "the key is read through its owner"
    assert record[1] == ("type", "entry"), "the key is the entry identity, read with the facts the row states"
    for row in rows:
        key = codebase_state.join_key(record, row)
        assert key == state_coverage.ownership_key(row["type"], row["entry"], row), row
        assert key + (row[ownership.SOURCE_FIELD],) == ownership.row_key(row), row
    keys = [codebase_state.join_key(record, row) for row in rows]
    assert len(set(keys)) == len(keys), "one key names one row"
    assert record[2] == "the entry identity", "the table names the fact the key joins on"


def test_the_join_key_for_the_edge_record_is_the_pair_of_entry_identities(tmp_path):
    """An edge row is a pair fact, so its key is the referrer's identity, the target's identity, the matrix row and
    the entry name: the join `reference_edges.py` rule 2 states, read through the row shape.
    """
    rows = _rows(CODEBASE_FIXTURE, tmp_path)
    edges, manifest = rows[reference_edges], rows[unit_manifest]
    assert edges, "the pin reads a record with content"
    units = {row["directory"] for row in manifest}
    record = JOIN_RECORDS[reference_edges]
    for row in edges:
        key = codebase_state.join_key(record, row)
        assert key == (row["referrer"], row["target"], row["type"], row["entry"]), row
        # Each half of the pair is a unit the manifest names, so the key joins to the manifest row.
        assert row["referrer"] in units and row["target"] in units, row
    keys = [codebase_state.join_key(record, row) for row in edges]
    assert len(set(keys)) == len(keys), "one key names one row"
    assert record[2] == "the pair of entry identities", "the table names the fact the key joins on"
    assert record[1] == reference_edges.FIELD_ORDER, "the key is the row's own four fields"


def test_the_join_key_for_the_site_record_is_the_unit_identity_read_as_directory(tmp_path):
    """The site row joins to the manifest row on `directory`, the same join the other records use, so the site key is
    the unit identity and the module states no second unit rule.
    """
    rows = _rows(CODEBASE_FIXTURE, tmp_path)
    sites, manifest = rows[site_data], rows[unit_manifest]
    assert sites, "the pin reads a record with content"
    units = {codebase_state.join_key(JOIN_RECORDS[unit_manifest], row) for row in manifest}
    record = JOIN_RECORDS[site_data]
    keys = [codebase_state.join_key(record, row) for row in sites]
    for key in keys:
        assert key in units, "the row joins to a unit the manifest names"
    assert len(set(keys)) == len(keys), "one key names one row"
    assert record[2] == "the unit identity", "the table names the fact the key joins on"
    assert record[1] == ("directory",), "the key is the field the record states"


# --- 2. The merge rule ---------------------------------------------------------


def test_the_run_rows_replace_the_codebase_rows_for_the_rows_the_run_built(tmp_path):
    """The rule, stated once: for a key the run named the merged row is the run's row, and for a key only the
    codebase named the merged row is the row as the record states it.

    Measured 2026-11-22 on the committed fixtures, the kitchen-sink run as the codebase and the
    `address_objects.xml` run as the second run: the codebase's 11 manifest rows against the run's 1 give 11, with
    1 key replaced and the 10 rows for units the run did not build kept. `OWNERSHIP.json` goes from 61 rows to the
    run's 5 and the merge holds 62: 4 keys replaced and 1 added. The second run names no rows for the edge record
    and the site record, so the merge is the codebase's own rows for those two, and the run wrote no file for them.
    """
    codebase = _rows(CODEBASE_FIXTURE, tmp_path / "codebase")
    run_rows = _rows(RUN_FIXTURE, tmp_path / "run")
    for _name, module in DATA_RULE:
        merged = _merged(module, codebase[module], run_rows[module])
        record = JOIN_RECORDS[module]
        by_key = {codebase_state.join_key(record, row): row for row in merged}
        run_keys = {codebase_state.join_key(record, row) for row in run_rows[module]}
        assert len(by_key) == len(merged), (module.__name__, "one row per key")
        assert set(by_key) == {codebase_state.join_key(record, row) for row in codebase[module]} | run_keys, (
            module.__name__,
            "the merged set is the codebase's keys plus the run's keys",
        )
        for key, row in by_key.items():
            if key in run_keys:
                assert row in run_rows[module], (module.__name__, key, "the run's row replaced the codebase's row")
            else:
                assert row in codebase[module], (module.__name__, key, "a row for a unit the run did not build")
    counts = {
        unit_manifest: 11,
        ownership: 62,
        reference_edges: 9,
        site_data: 3,
    }
    measured = {module: len(_merged(module, codebase[module], run_rows[module])) for module in counts}
    assert measured == counts, measured


def test_the_merged_manifest_set_is_the_codebase_unit_set_read_through_the_one_unit_rule(tmp_path):
    """The merge names no unit set of its own. The run's set and the codebase's set are read through
    `unit_manifest.units`, the one rule that names a unit for a directory, an owner or an edge, over the rows each
    record read back through its own `parse_rows`; `codebase_state.py` reads that rule through `unit_manifest` and
    restates no row shape, so the scan pin that reads the merge module still reads it clean. Because the merge
    replaces the rows for the units the run built and keeps the rows for the units it did not, the merged set
    names no unit beyond the codebase's set and the run's set, and the run's set is inside it.

    Measured 2026-11-22 on the committed pair: 11 units read through `units` over the kitchen-sink record, 1 unit
    read through `units` over the `address_objects.xml` record, and the merged set is the same 11 units.
    """
    codebase = _rows(CODEBASE_FIXTURE, tmp_path / "codebase")
    run_rows = _rows(RUN_FIXTURE, tmp_path / "run")
    merged = _merged(unit_manifest, codebase[unit_manifest], run_rows[unit_manifest])
    codebase_set = unit_manifest.units(codebase[unit_manifest])
    run_set = unit_manifest.units(run_rows[unit_manifest])
    merged_set = unit_manifest.units(merged)
    assert codebase_set and run_set, "the pins read both runs through `parse_rows`"
    assert merged_set == codebase_set, (merged_set, codebase_set, "the merge adds no unit")
    assert set(run_set) <= set(merged_set), "the units the run built are inside the codebase's set"
    assert merged_set, "the codebase set names a unit the run read only through the record"


# --- 3. The byte rule between two runs -----------------------------------------


def test_a_record_with_no_existing_file_writes_the_bytes_a_single_run_writes_today(tmp_path):
    """A record with no existing file is the run's own set, in the order the record's own rule built it, so the merge
    writes the bytes a single run writes today and no committed golden changes. The golden set pins the same runs'
    `.tf` bytes, so this pin reads the record bytes against the bytes the same run wrote.

    Measured 2026-11-22 on the four cases the golden set names: the bytes agree for every record that has rows, and
    a record the run has no content for is written by no run, which is the rule that a file is written only when it
    has content.
    """
    for case in GOLDEN_CASES:
        out = tmp_path / case
        rows = _rows(case, out)
        for name, module in DATA_RULE:
            merged = codebase_state.merge_rows(JOIN_RECORDS[module], [], rows[module])
            assert merged == rows[module], (case, module.__name__, "no existing file is the run's own set")
            if rows[module]:
                assert module.render(merged).encode("utf-8") == (out / name).read_bytes(), (case, name)
            else:
                assert not (out / name).is_file(), (case, name, "a record with no rows is not written")


# --- 4. No run field, and the order read through each record's own rule ---------


def test_the_merge_adds_no_field_so_a_merged_row_reads_back_as_itself(tmp_path):
    """The merge holds no run field and no timestamp: a merged row is one of the record's own rows, it states only
    the fields the record declares, and it reads back through `parse_rows` as itself.

    `ownership.SOURCE_FIELD` names the source the parse read, not the run, so a merged set cannot state which run
    wrote a row.
    """
    codebase = _rows(CODEBASE_FIXTURE, tmp_path / "codebase")
    run_rows = _rows(RUN_FIXTURE, tmp_path / "run")
    for _name, module in DATA_RULE:
        merged = _merged(module, codebase[module], run_rows[module])
        assert merged, (module.__name__, "the pin reads a record with content")
        for row in merged:
            assert tuple(row) == tuple(SHAPES[module]), (module.__name__, row, "no field the record does not declare")
            assert row in codebase[module] or row in run_rows[module], (module.__name__, row, "no fact the merge adds")
        # The printed form reads back as the same rows, so the data rule's reader stays the only shape rule.
        assert module.parse_rows(module.render(merged)) == merged, module.__name__


def test_the_order_of_a_merged_set_is_the_order_each_record_states_not_the_order_of_writes(tmp_path):
    """The order is read through each record's own order rule: `unit_manifest.FACT_KEYS` for the manifest,
    `ownership.row_key` for the ownership record, `reference_edges.FIELD_ORDER` for the edge record, and for the site
    record the order the join key states, because `site_data.py` states no order rule for a row it reads back. The
    condition that a site row names no facts, so it cannot state the identity order on its own, is recorded in
    `backlog.md`. Reading the two sets in the other order answers the same rows in the same order, so no
    order-of-writes fact appears.

    The manifest is the record whose own order rule is not the join-key order, which is why the order is read through
    the record's rule and not through the key: measured on the kitchen-sink run, the two orders differ.
    """
    codebase = _rows(CODEBASE_FIXTURE, tmp_path / "codebase")
    run_rows = _rows(RUN_FIXTURE, tmp_path / "run")
    for _name, module in DATA_RULE:
        record = JOIN_RECORDS[module]
        forward = codebase_state.merge_rows(record, codebase[module], run_rows[module])
        backward = codebase_state.merge_rows(record, list(reversed(codebase[module])), list(reversed(run_rows[module])))
        assert forward == backward, (module.__name__, "the order is not the order of writes")
        order = record[3]
        if order is None:
            keys = [codebase_state.join_key(record, row) for row in forward]
            assert keys == sorted(keys), (module.__name__, "the join key order, the record states no order rule")
        elif callable(order):
            values = [order(row) for row in forward]
            assert values == sorted(values), (module.__name__, "the record's own order rule")
        else:
            values = [tuple(row[field] for field in order) for row in forward]
            assert values == sorted(values), (module.__name__, "the record's own order rule")
    manifest = JOIN_RECORDS[unit_manifest]
    merged_manifest = _merged(unit_manifest, codebase[unit_manifest], run_rows[unit_manifest])
    keys = [codebase_state.join_key(manifest, row) for row in merged_manifest]
    assert keys != sorted(keys), "the manifest row order is the fact order, not the join-key order"


# --- 5. The module states no rule an owner states ------------------------------


def test_the_module_states_no_rule_an_owner_states_and_writes_no_file():
    """`codebase_state.py` states the join key as data and the merge as one function, and reads every other rule
    through an owner, so the `src/` scans read it clean: the writer scan, the environment-name scan, the console-line
    scan and the second-naming-rule scan. It names no file, so the gate's data rule stays the only data rule over the
    four records.
    """
    source = Path(codebase_state.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    defined = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    defined |= {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    for name in (
        "sanitize",
        "facts_of",
        "fact",
        "unit_name",
        "named_fact",
        "directory_name",
        "identity_digest",
        "row_key",
        "ownership_key",
        "units",
        "unit_directories",
        "parse_rows",
        "render",
        "render_csv",
        "read_text",
        "write",
        "write_file",
        "root_path",
        "unit_path",
        "console_line",
        "data_file",
    ):
        assert name not in defined, (name, "the module reads this rule through its owner")
    for token in ("CONSOLE_PREFIX", "os.environ", "API_KEY_ENV", "open(", "write_text", "Path(", ".json"):
        assert token not in source, (token, "the module names no file, no writer and no path rule of its own")

    imported = {alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names}
    house = {path.name[:-3] for path in SRC_DIR.glob("*.py")}
    assert imported <= house, imported
    assert imported == {"ownership", "reference_edges", "site_data", "state_coverage", "unit_manifest"}, (
        "the module reads the row shapes and the key rule through the owners it imports",
        imported,
    )
    assert not hasattr(codebase_state, "write_file"), "the single writer writes the file"

    # The table is the join key as data: one row per record, each naming the module that owns the shape, the fields
    # the key is built from, the fact it joins on, the order rule and the key rule it reads through an owner.
    assert len(codebase_state.JOIN_KEYS) == 4, "one join key per record"
    for record in codebase_state.JOIN_KEYS:
        module, fields, fact, order, key_rule = record
        assert module in {m for _name, m in DATA_RULE}, record
        assert fields and all(isinstance(field, str) for field in fields), record
        assert fact, record
        assert order is None or callable(order) or all(isinstance(field, str) for field in order), record
        assert key_rule is None or key_rule is state_coverage.ownership_key, record
