"""F2.5 order-preserving policy emission, read through the iterated block (Epic 9 Piece 19).

Pins the chain semantics on the dedicated multi-DG fixture and on the committed goldens:

- one block per rule type per unit, in the file the coverage matrix row names, and the block reads the `locals`
  map that is the printed form of that unit's rows;
- the block's name and the map's name are the one name the matrix row's `output_file` stem names, read through
  `rule_data.locals_name`, so the block, the map, the `.json` form and the `.csv` form read one name;
- the apply order comes from the key order: the ordinals run 1..N inside a chain in the order the export lists the
  rules, the printed entry order is the sorted key order, and `position` anchors every instance at the end of the
  rulebase, so the per-instance pivot and `depends_on` dropped (Epic 9 decision 4);
- a chain never crosses a unit, because the chain group (device group, virtual system) is two of the five unit
  facts and the row's `directory` is the join, so the key's digest half is the digest the directory names;
- the same order contract across the accepted corpus, read through the pipeline: the printed entry order is the
  key order, the key order is the XML order, and no unit in the corpus holds more than one chain per rule type,
  which is the case the two orders could differ on (Epic 9, Piece 21).

The rule-shape parser and the chain check are read through `tests/conftest.py` (§1.1), the one place the shape is
read, so this module and `tests/test_real_or_report.py` share one implementation of the chain semantics.
"""

from pathlib import Path

import pytest

import container_coverage
import entry_coverage
import import_blocks
import naming
import panorama_to_terraform
import rule_data
import sanity_checks
import xml_input
from conftest import (
    FIXTURES_DIR,
    GOLDEN_DIR,
    SAMPLE_CONFIG,
    check_chain_semantics,
    corpus_fixtures,
    file_text,
    parts,
    rule_blocks,
    run_pipeline,
    run_script,
    tf_files,
)

# The goldens this piece reads: the case and the source the case is the output of. `tests/test_golden_files.py`
# holds the byte comparison; this module reads the order the source states. No test module imports another test
# module, so the pair is stated here for the two cases the pins read.
GOLDEN_CASES = {
    "sample": SAMPLE_CONFIG,
    "kitchen_sink": FIXTURES_DIR / "kitchen_sink.xml",
}

# The chain groups the fixture states, in first-seen order, and the rule names inside each in export order.
EXPECTED_SECURITY = [
    ("Alpha-DG", ["alpha-rule-1", "alpha-rule-2", "alpha-rule-3"]),
    ("Beta-DG", ["beta-rule-1", "beta-rule-2"]),
    ("Gamma-DG", ["gamma-rule-1"]),
]
EXPECTED_NAT = [
    ("Alpha-DG", ["alpha-nat-1", "alpha-nat-2"]),
]


@pytest.fixture(scope="module")
def generated(tmp_path_factory) -> Path:
    """Generate the multi-DG fixture once for the whole module."""
    out = tmp_path_factory.mktemp("policy_order")
    proc = run_script("panorama_to_terraform.py", str(FIXTURES_DIR / "policy_order.xml"), "--output-dir", str(out))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return out


def _rows(resource_type: str, source: Path) -> list[dict]:
    """The rows the run's rule names for one rule type: the parse, read through `rule_data`.

    The key, the ordinal and the unit join are read through the module that owns them, so this helper states no key
    rule, no ordinal rule and no unit rule of its own, and the pin compares the printed shape against the rows
    rather than restating how a key is built.
    """
    parser = panorama_to_terraform.PanoramaParser(xml_input.parse_xml(source))
    rules = getattr(parser, f"parse_{resource_type.split('_')[1]}_rules")()
    return rule_data.build_rows(resource_type, rules, naming.sanitize)


# --- Fixture: security rules -----------------------------------------------


def test_security_chains_emit_one_block_per_unit_in_key_order(generated):
    """One block per unit, the units in first-seen order, and the entries in the XML order inside each chain."""
    blocks = rule_blocks(file_text(tf_files(generated), "security_rules.tf"), "panos_security_policy_rules")
    check_chain_semantics(blocks, "panos_security_policy_rules", EXPECTED_SECURITY, "security fixture")
    assert [b["group"] for b in blocks] == ["Alpha-DG", "Beta-DG", "Gamma-DG"], "security fixture"
    # The order fact is the key order, so the position the block prints is the same anchor for every instance.
    assert all(block["where"] == "last" for block in blocks), "security fixture"


def test_a_single_rule_unit_prints_one_entry(generated):
    """Gamma-DG has one rule: the anchor, and one entry keyed by the first ordinal."""
    blocks = rule_blocks(file_text(tf_files(generated), "security_rules.tf"), "panos_security_policy_rules")
    gamma = [b for b in blocks if b["group"] == "Gamma-DG"]
    assert len(gamma) == 1
    assert gamma[0]["where"] == "last"
    assert [entry["ordinal"] for entry in gamma[0]["entries"]] == [f"{1:0{rule_data.ORDINAL_WIDTH}d}"]


def test_a_chain_never_crosses_a_unit(generated):
    """F3.2: the chain group (device group, virtual system) is two of the five unit facts, so a chain lands in one
    unit and the block written for that unit holds exactly that chain's rows.

    The rows are read through `rule_data`, so the key, the ordinal and the unit join are the rule that owns them,
    and the pin compares the printed shape against the rows instead of restating how a key is built. A rule that
    repeats a name in another virtual system is another block in another unit's file.
    """
    resource_type = "panos_security_policy_rules"
    parser = panorama_to_terraform.PanoramaParser(xml_input.parse_xml(FIXTURES_DIR / "policy_order.xml"))
    rules = parser.parse_security_rules()
    rows = rule_data.build_rows(resource_type, rules, naming.sanitize)
    files = tf_files(generated)
    seen = 0
    for chain in rule_data.chains(rules):
        chain_rows = rows[seen : seen + len(chain)]
        seen += len(chain)
        units = {row["directory"] for row in chain_rows}
        assert len(units) == 1, f"a chain crosses a unit: {chain}"
        unit = next(iter(units))
        block = rule_blocks(files[f"{unit}/security_rules.tf"], resource_type)[0]
        assert [entry["key"] for entry in block["entries"]] == sorted(row["key"] for row in chain_rows), chain
        # Inside a chain the sorted key order is the order the export lists the rules.
        assert sorted(row["key"] for row in chain_rows) == [row["key"] for row in chain_rows], chain
        names = [f'"{row["entry"]}"' for row in chain_rows]
        assert [entry["fields"]["name"] for entry in block["entries"]] == names, chain


# --- Fixture: NAT rules ------------------------------------------------------


def test_nat_chains_follow_the_same_semantics(generated):
    blocks = rule_blocks(file_text(tf_files(generated), "nat_rules.tf"), "panos_nat_policy_rules")
    check_chain_semantics(blocks, "panos_nat_policy_rules", EXPECTED_NAT, "nat fixture")


# --- Goldens -----------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_file",
    [
        "sample/security_rules.tf",
        "sample/nat_rules.tf",
        "kitchen_sink/security_rules.tf",
        "kitchen_sink/nat_rules.tf",
    ],
    ids=lambda p: p.replace("/", "_"),
)
def test_goldens_print_the_rows_in_the_chain_order(fixture_file):
    """The committed goldens already follow the chain contract.

    F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the case holds one part per unit, so the pin reads the parts as
    paths from the case directory. One part is one unit, so the pin reads one block per part and compares the
    printed entry order with the order the rule names for that unit, read through `rule_data`.
    """
    case, name = fixture_file.split("/")
    written = parts(sanity_checks.read_tf_files(GOLDEN_DIR / case), name)
    assert written, f"no golden part named {name} in {case}"
    resource_type = "panos_security_policy_rules" if "security" in name else "panos_nat_policy_rules"
    rows = _rows(resource_type, GOLDEN_CASES[case])
    for path, text in written.items():
        blocks = rule_blocks(text, resource_type)
        assert len(blocks) == 1, (path, blocks)
        block = blocks[0]
        unit = Path(path).parent.name
        unit_rows = [row for row in rows if row["directory"] == unit]
        assert unit_rows, path
        # The printed order is the sorted key order, and inside a unit that order is the XML order.
        assert [entry["key"] for entry in block["entries"]] == sorted(row["key"] for row in unit_rows), path
        assert [entry["key"] for entry in block["entries"]] == [row["key"] for row in unit_rows], path
        assert [entry["fields"]["name"] for entry in block["entries"]] == [f'"{row["entry"]}"' for row in unit_rows], (
            path
        )
        assert block["local"] == rule_data.locals_name(resource_type), path
        assert block["for_each"] == f"local.{rule_data.locals_name(resource_type)}", path


# --- Across the corpus -------------------------------------------------------


def test_the_key_order_is_the_xml_order_across_the_corpus(tmp_path):
    """F2.5, read across the accepted corpus: the apply order is the key order and the key order is the XML order.

    Inside one iterated block the apply order is the order the printed map holds its entries, so the pin compares
    the printed order with the order the parse listed the rules for that unit. The two orders can only differ
    where one unit holds more than one chain, because the ordinal half of the key counts inside one chain, so the
    pin reads that case as well. The parse answer for a rule type is the method the container table names for the
    row, the file is the one the matrix row names, and the printed shape is read through the one rule-shape
    parser, so this pin states no rule type, no file name and no key rule of its own.

    Measured 2026-11-24 on the 69 accepted fixtures: 18 blocks over 9 fixtures and 37 rows, no unit holds more
    than one chain for a rule type, and every block prints its entries in the order the export lists them.
    """
    rule_rows = [
        row
        for row in container_coverage.CONTAINER_TABLE
        if entry_coverage.row_detail(row) in import_blocks.rule_types()
    ]
    assert len(rule_rows) == len(import_blocks.rule_types()), "the container table names one row per rule type"

    blocks_read = 0
    rows_read = 0
    entries_read = 0
    units_with_more_than_one_chain = 0
    for fixture in corpus_fixtures():
        out = tmp_path / fixture
        # An accepted fixture cannot be refused, so no guard is needed here.
        parser = run_pipeline(panorama_to_terraform, fixture, out)
        assert parser is not None, fixture
        files = tf_files(out)
        for row in rule_rows:
            resource = entry_coverage.row_detail(row)
            rules = getattr(parser, row.method)()
            if not rules:
                continue
            rows = rule_data.build_rows(resource, rules, naming.sanitize)
            rows_read += len(rows)
            chains_by_unit: dict[str, list[list[dict]]] = {}
            for chain in rule_data.chains(rules):
                chain_rows = rule_data.build_rows(resource, chain, naming.sanitize)
                units = {chain_row["directory"] for chain_row in chain_rows}
                assert len(units) == 1, f"a chain crosses a unit: {fixture} {resource} {chain}"
                chains_by_unit.setdefault(next(iter(units)), []).append(chain)
            units_with_more_than_one_chain += sum(1 for chains in chains_by_unit.values() if len(chains) > 1)
            file_name = entry_coverage.MATRIX_BY_RESOURCE[resource]["output_file"]
            written = parts(files, file_name)
            assert written, (fixture, file_name)
            for path, text in written.items():
                unit = Path(path).parent.name
                block = rule_blocks(text, resource)
                assert len(block) == 1, (path, block)
                blocks_read += 1
                unit_rows = [built_row for built_row in rows if built_row["directory"] == unit]
                assert unit_rows, path
                entries = block[0]["entries"]
                entries_read += len(entries)
                # The apply order is the printed order, and the printed order is the key order.
                assert [entry["key"] for entry in entries] == sorted(entry["key"] for entry in entries), path
                # The key order is the XML order: the rows are the parse answer, in the order the export lists
                # the rules, so the printed keys are the keys in that order.
                assert [entry["key"] for entry in entries] == [built_row["key"] for built_row in unit_rows], path
                assert [entry["ordinal"] for entry in entries] == [
                    f"{position:0{rule_data.ORDINAL_WIDTH}d}" for position in range(1, len(unit_rows) + 1)
                ], path

    assert blocks_read, "the corpus writes rule blocks, so the pin measures content"
    assert rows_read == entries_read, "one entry per row, so the map is the row set"
    assert units_with_more_than_one_chain == 0, "the case the two orders could differ on"
