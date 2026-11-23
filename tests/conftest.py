"""Shared test fixtures and the definitions the tests read.

The tool's modules live in `src/` and are not an installed package. The import rule is in
`docs/ARCHITECTURE.md` §1.1: `src/` is one flat namespace, so a test imports a module by plain name, and
`pyproject.toml` `pythonpath = ["src"]` is the only place the path is stated for tests. This file builds the
paths a test reads the layout through, states no second path rule, and holds the definitions more than one
test module reads: the terraform binary, the two resource-line patterns, the rule-block parser, the record
read-back the Epic 11 pins read (the join key per record, and the four records read back through each module's
`parse_rows`), and the two runs the partial-run pins read (one run writes a codebase, a second run writes into a
copy of its output). A test module does not define its own copy of any of them, and no test module imports another
test module.
"""

import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import api_requests
import codebase_state
import commit_actions
import entry_coverage
import import_blocks
import panorama_to_terraform
import rule_data
import sanity_checks
import source_fetch
import split_device_groups
import write_path
import xml_input

TESTS_DIR = Path(__file__).parent
REPO_ROOT = TESTS_DIR.parent
SRC_DIR = REPO_ROOT / "src"
TOOLS_DIR = REPO_ROOT / "tools"
EXAMPLES_DIR = REPO_ROOT / "examples"
SAMPLE_CONFIG = EXAMPLES_DIR / "sample_panorama_config.xml"
FIXTURES_DIR = TESTS_DIR / "fixtures"
GOLDEN_DIR = TESTS_DIR / "golden"
# The committed pair the reference-source pins read through `partial_run`: the run that builds a whole codebase,
# and a second run that names one unit inside it. Both records are read through `parse_rows`, the one reader of
# the row shape, so this is the one place the pair's names are stated.
CODEBASE_FIXTURE = "kitchen_sink.xml"
RUN_FIXTURE = "address_objects.xml"
# The committed API responses (F8.4). A response is not a Panorama export, so the scan and the fixture
# assembler never read it: `FIXTURES_DIR` is the corpus, and this is a separate set (§1.1).
RESPONSES_DIR = TESTS_DIR / "responses"
# The committed tflint material (Piece 11): the content that violates each rule the gate's tflint check reads, and
# the answer tflint 0.66.0 with the bundled ruleset 0.17.0 gave for it, measured 2026-11-18. Test material, so no
# tool rule reads it and it is not corpus material.
TFLINT_DIR = TESTS_DIR / "tflint"
TERRAFORM = shutil.which("terraform")
# The one place the test set resolves the tflint binary, so no pin resolves it a second time. A pin that runs the
# binary skips only when this answers nothing, and asserts on a non-zero run.
TFLINT = shutil.which("tflint")

# Every `resource "panos_x" "y" {` line in a Terraform file, read through this file by the test set.
# Two named patterns, each with the rule it serves. `RESOURCE_RE` answers the resource type, which the pins
# that read the emitted type set read. `RESOURCE_ADDRESS_RE` answers the same line with the local name
# captured, for `tests/test_dependency_wiring.py`, which reads `findall` as (type, local name) pairs, so a
# one-group pattern cannot serve it. Both require the block brace, so neither pattern is broader than the
# other, and no pin passes because a merged pattern is wider. Measured 2026-11-19 on the committed goldens
# (87 `.tf` files) and the output of a corpus run (584 `.tf` files): the three shapes the test set held
# before answer the same 387 matches, and 0 resource lines lack the trailing brace, so the brace changes
# nothing on the measured material; the real difference is the capture groups (42 distinct types, 238
# distinct addresses). The numbers measured on 2026-11-13 (414 matches and 262 addresses) no longer hold,
# because the four `*_policy_rules` types print one iterated block per rule type per unit instead of one
# block per rule, which is the same material read through the emitter change, not a wider or narrower pattern.
# The decision is recorded in `acceptance.md`.
RESOURCE_RE = re.compile(r'resource\s+"([a-z0-9_]+)"\s+"[^"]+"\s*\{')
RESOURCE_ADDRESS_RE = re.compile(r'resource\s+"([a-z0-9_]+)"\s+"([^"]+)"\s*\{')


def tf_files(output_dir) -> dict[str, str]:
    """The `.tf` files a run wrote, keyed by the path from the output directory.

    F6.10.3 (`docs/CODEBASE_ASSEMBLY.md` §14): the run writes one directory per unit, so a test reads the
    file set the way the gate reads it, through `sanity_checks.read_tf_files`. A test that names a file
    names the path, because a per-unit file names its unit only by its directory.
    """
    return sanity_checks.read_tf_files(Path(output_dir))


def parts(files: dict[str, str], name: str) -> dict[str, str]:
    """The parts of one file name across the unit set, keyed by the path the reader names (F6.10.3, §14).

    A per-unit file names its unit only by its directory, so one file shape holds one part per unit. A test
    that pins one file for one unit reads the part; a test that pins the shape across the run reads the
    parts in path order.
    """
    return {key: files[key] for key in sorted(files) if Path(key).name == name}


def file_text(files: dict[str, str], name: str) -> str:
    """The text one file name holds across the unit set, with the parts in path order.

    A test that pins one emitter's whole file reads the parts the run wrote for every unit, so the same pin
    holds for a file set the run wrote one file per unit. `name` is the file name, not a path.
    """
    return "".join(parts(files, name).values())


def written_bytes(output_dir) -> dict[str, bytes]:
    """The bytes a run wrote, keyed by the path from the output directory (F6.10.3, §14).

    The run writes the root set at the root and the unit set inside one directory per unit, so a test that
    pins two runs writing the same bytes compares the whole layout, not only the files at the root.
    """
    out = Path(output_dir)
    return {str(path.relative_to(out)): path.read_bytes() for path in sorted(out.rglob("*")) if path.is_file()}


def tf_bytes(output_dir) -> dict[str, bytes]:
    """The `.tf` bytes a directory holds, keyed by the path from that directory (F6.10.3, §14).

    A golden case is the output of one run, so the `.tf` set sits inside the unit directories and not at the
    case root: a read of `glob('*.tf')` at the case root answers nothing, and a pin built on it compares two
    empty sets. Keyed by the file name, two units that write the same file name collapse, so the key is the
    path. This is the shape `tests/test_golden_files.py` reads. A pin that compares two directories through it
    states that both sets are not empty, so the pin measures content.
    """
    return {key: value for key, value in written_bytes(output_dir).items() if Path(key).suffix == ".tf"}


# --- The predefined read content, shared by the modules that read it (F8.1) -----

# The two shapes the one scope path definition validates for the built-in place: the place, and one built-in
# entry inside it. Two test modules read the same content, so it is stated here (§1.1). It is harness content,
# not a committed response: no committed response names a predefined path, so the pins read it through the
# injected producer and the response set is unchanged.
PREDEFINED_PLACE_BODY = (
    "<predefined>\n<url-list>\n"
    '<entry name="url-list"><description>built-in</description></entry>\n'
    "</url-list>\n</predefined>\n"
)
PREDEFINED_ENTRY_BODY = '<entry name="url-list"><description>built-in</description></entry>\n'


# --- The rule row set, shared by the modules that read it (Epic 9, Phase 9D) -----

# The rule-type set, read through the module that owns it, so no test module states its own list.
RULE_TYPES = tuple(sorted(import_blocks.rule_types()))


def data_file_set(output_dir) -> list[str]:
    """The files the gate's data count names: the four records at the codebase root, plus the rule data pair's
    data member inside each unit directory its own rows name (Epic 9, rule 5).

    The names are read through `rule_data`, the module that owns the row shape and the three forms, and the unit
    set through `sanity_checks.unit_directories`, which reads the manifest record, so this states no file-name rule
    and no unit rule of its own. The printed member is not a data file, the way `site.auto.tfvars` is not, because
    it is a printed form and not a reader input. A pin that compares the report's data count with this set measures
    the count through the same derivation the rule states.
    """
    out = Path(output_dir)
    names = [name for name, _shape in sanity_checks.DATA_FILES if (out / name).is_file()]
    for resource in RULE_TYPES:
        for directory in sanity_checks.unit_directories(out):
            path = write_path.unit_path(out, directory, rule_data.data_file(resource))
            if path.is_file():
                names.append(str(path.relative_to(out)))
    return sorted(names)


# --- The records read back as data, shared by the merged-set pins (Epic 11, Piece 11B.3) ---

# The join key per record, read through the table `codebase_state.py` states, so no test module states a table of its
# own. Three test modules read this copy: `tests/test_codebase_state.py`, `tests/test_reference_edges.py` and
# `tests/test_ownership.py`. The two that read the table without this copy, `tests/test_data_file_gate.py` and
# `tests/test_unit_manifest.py`, read it through its owner (`codebase_state.JOIN_KEYS`), so the table is stated once.
JOIN_RECORDS = {record[0]: record for record in codebase_state.JOIN_KEYS}


def record_rows(output_dir) -> dict:
    """The four records read back through each record module's `parse_rows`, keyed by module.

    The set is `sanity_checks.DATA_FILES`, read through its owner, so this states no file set of its own, and each
    row is read through the module that owns its shape. A record the run has no content for is not written, so it
    answers no rows. A merged set is read through `codebase_state.merge_rows`, the one merge rule, so no test module
    states a merge of its own.
    """
    out = Path(output_dir)
    rows = {}
    for name, module in sanity_checks.DATA_FILES:
        path = out / name
        rows[module] = module.parse_rows(path.read_text(encoding="utf-8")) if path.is_file() else []
    return rows


# --- The pattern the partial-run pins read (Epic 11, Piece 11B.4) -------------


# Three test modules read the same two runs: one run writes a codebase, and a second run writes into a copy of
# its output, so the second run's own unit set is smaller than the set the tree holds. The pins read the pattern
# from here, so no test module states it a second time. `run_pipeline` runs in process, so the ledger is the second
# run's own ledger, and its unit set is `unit_manifest.units` over it. The copy is the codebase the second run
# wrote into, so the bytes inside a unit the second run did not build are the bytes the first run wrote.
def partial_run(first_fixture: str, second_fixture: str, out_dir) -> tuple:
    """The two runs, as the pattern states them: returns (codebase_dir, partial_dir, second_run_parser)."""
    codebase = Path(out_dir) / "codebase"
    partial = Path(out_dir) / "partial"
    first = run_pipeline(panorama_to_terraform, first_fixture, codebase)
    assert first is not None, f"{first_fixture}: the run refused the input"
    shutil.copytree(codebase, partial)
    second = run_pipeline(panorama_to_terraform, second_fixture, partial)
    assert second is not None, f"{second_fixture}: the run refused the input"
    return codebase, partial, second


def write_merged_records(codebase_dir, run_dir, out_dir) -> dict:
    """The merged record set, written at the root of `out_dir` through `write_path`, and returned as rows keyed by
    module.

    Both row sets are read through `record_rows`, the merge is `codebase_state.merge_rows` with the key read through
    `JOIN_RECORDS`, and each row shape is read through its own module's `parse_rows`, so this states no file set, no
    key and no merge of its own. A pin that reads the data rule over a codebase that holds rows from two runs reads
    the record as the tool wrote it, so no pin builds a row by hand.
    """
    merged = {}
    code_rows = record_rows(codebase_dir)
    run_rows = record_rows(run_dir)
    for name, module in sanity_checks.DATA_FILES:
        rows = codebase_state.merge_rows(JOIN_RECORDS[module], code_rows[module], run_rows[module])
        merged[module] = rows
        write_path.write_file(write_path.root_path(Path(out_dir), name), module.render(rows))
    return merged


def run_records(module_name, source, out_dir) -> dict:
    """Run the converter on committed material and return the records read back.

    `source` is a committed file, so a pin reads the run through the tool and every row through the module that owns
    its shape: no pin builds a row by hand.
    """
    result = run_script(module_name, str(source), "--output-dir", str(out_dir))
    assert result.returncode == 0, result.stdout + result.stderr
    return record_rows(out_dir)


# --- The content the `number` reading-rule pins read (F7.1 rule 11) ------------

# One text the signed-integer rule cannot read, the `number` field the pins read the rule through, and the fact
# the reading rule states for that text. Two test modules read this pair, so it lives in this file:
# `tests/test_parse_helpers.py` pins the three answers the reading rule gives for a `number` field, and
# `tests/test_entry_coverage.py` pins the entry line that prints the fact. The field is one the shape table
# states as `number`, so the pins read the shape word through the table and state no shape of their own.
UNREAD_NUMBER_TEXT = "not-a-number"
NUMBER_FIELD = "tag"
UNREAD_NUMBER_FACT = f"{NUMBER_FIELD} {UNREAD_NUMBER_TEXT!r} is not a signed integer"

# --- The corpus read rule the corpus pins read (F3.8, F3.9) ---------------------


def input_refusal(path) -> str | None:
    """What the tool's input rule answers for one committed fixture: the refusal reason, or None when it accepts.

    The rule is `xml_input.check_bytes`, then the parse, read on the committed bytes. This is the one place the
    test set decides which fixtures a corpus pin reads, so the exclusion is the tool's read rule and not a file
    name. `tools/build_kitchen_sink.py` states the same rule for the same reason, and
    `tests/test_build_kitchen_sink.py` pins that the two agree on the committed corpus. A fixture this answers
    None for cannot fail the parse, so a pin that reads it needs no guard.
    """
    try:
        xml_input.parse_xml(path)
    except xml_input.UnsafeInputError as exc:
        return str(exc)
    except ET.ParseError as exc:
        return f"the parse cannot read it: {exc}"
    return None


def corpus_fixtures() -> list[str]:
    """The fixture names a corpus pin reads: the committed corpus, less the fixtures the read rule refuses.

    Names, in the order the corpus pins read them, so a pin's failure message names the fixture. The rule is
    `input_refusal`; a fixture name is not a rule.
    """
    return [path.name for path in sorted(FIXTURES_DIR.glob("*.xml")) if input_refusal(path) is None]


def declared_terraform_minimum() -> str:
    """Read the Terraform minimum through its owner, `commit_actions.TERRAFORM_MINIMUM`.

    The minimum has one owner in `src/` (Epic 12 decision 2), so a pin reads the version through this helper
    instead of stating it as a string. The pins that read the generated `terraform` block, the generated
    `README.md` line and the generated `actions.tf` header read the version here, so a change to the owner moves
    the pins with it, and the committed goldens are compared against the same value. The provider version has the
    same shape through `declared_provider`, which reads it from a golden `provider.tf`; the minimum is read from
    the module that owns it, because a pin cannot read an owner through a copy of the bytes it writes.
    """
    return commit_actions.TERRAFORM_MINIMUM


def declared_provider() -> tuple[str, str]:
    """Read the panos provider source and version from the golden provider.tf.

    The golden provider.tf is the single source of truth for which provider
    version the tests verify against (F2.1 pins it). F6.10.3: `provider.tf` is a unit-set file, so a
    golden case holds one per unit, and each states the same provider block, so any one gives the version.
    """
    path = sorted((GOLDEN_DIR / "sample").rglob("provider.tf"))[0]
    text = path.read_text()
    block = re.search(r"panos\s*=\s*\{([^}]*)\}", text, re.S).group(1)
    source = re.search(r'source\s*=\s*"([^"]+)"', block).group(1)
    version = re.search(r'version\s*=\s*"([^"]+)"', block).group(1)
    return source, version


def emitted_types() -> set[str]:
    """The set of panos resource types emitted across the committed goldens."""
    types: set[str] = set()
    for path in sorted(GOLDEN_DIR.rglob("*.tf")):
        for m in RESOURCE_RE.finditer(path.read_text()):
            types.add(m.group(1))
    return types


# --- The rule-shape parser the policy pins read (F2.5, Epic 9 Piece 19) -------

# `tests/test_policy_order.py`, `tests/test_real_or_report.py` and `tests/test_edge_cases.py` all read these
# functions, so they live in the one shared helper file (§1.1) and no module defines its own copy. The emitter
# prints one `for_each` block per rule type per unit, reading the map that is that unit's rows, so the parser reads
# two things per unit: the map and the one block that reads it. The generated shape is fixed, so small structural
# regexes are enough: a resource block ends at the first newline followed by a column-0 brace, and a map entry is
# the block that starts at four spaces inside the map body.

_ENTRY_FIELD_INDENT = "      "
_MAP_ENTRY_RE = re.compile(r'    "([^"]+)" = \{\n(.*?)\n    \}', re.S)


def _search_one(body: str, pattern: str):
    m = re.search(pattern, body, re.S)
    return m.group(1) if m else None


def _entry_fields(body: str) -> dict[str, str]:
    """One map entry as the file prints it: the field name -> the text the file prints for it, in print order.

    A field whose value is an object prints over several lines, so the lines deeper than the field's own indent
    belong to the field that started them. The text is the printed form, so a reference reads as the reference and
    a value reads as the value: the block body prints only `each.value.<field>`, and the entry is the only place a
    row value appears.
    """
    fields: dict[str, str] = {}
    for line in body.split("\n"):
        text = line[len(_ENTRY_FIELD_INDENT) :]
        if line.startswith(_ENTRY_FIELD_INDENT) and " = " in text:
            name, value = text.split(" = ", 1)
            fields[name] = value
        elif fields:
            fields[list(fields)[-1]] += "\n" + line
    return fields


def rule_blocks(text: str, resource_type: str) -> list[dict]:
    """The iterated rule shape, in file order: one answer per unit, the block and the map it reads.

    Each answer states the block's local name, which is also the map name and the matrix row's stem read through
    `rule_data.locals_name`; the `for_each` reference; the location name the block states, which is the chain group
    the block belongs to; the `position` anchor; the block's own field names in print order; and the map's entries
    in the order the file prints them, which is the sorted key order. An entry states its key, the ordinal and
    digest halves of that key, and the printed text of each field.

    `pivot` and `depends_on` are not part of the answer, because instances inside one block create in key order
    (Epic 9 decision 4) and `pivot` stays a row column of the data record the block does not print. A block reads
    the map the emitter printed for the same unit, and the emitter prints the map before the block, so the parser
    pairs a block with the map occurrence that ends before it.
    """
    blocks = []
    pattern = re.compile('resource "' + re.escape(resource_type) + r'" "([^"]+)" \{(.*?)\n\}', re.S)
    map_pattern = re.compile(r"locals \{\n  ([a-z_][\w]*) = \{\n(.*?)\n  \}\n\}", re.S)
    for m in pattern.finditer(text):
        local, body = m.group(1), m.group(2)
        map_name = _search_one(body, r"for_each = local\.([a-z_][\w]*)")
        entries = []
        for map_m in map_pattern.finditer(text[: m.start()]):
            if map_m.group(1) != map_name:
                continue
            entries = [
                {
                    "key": match.group(1),
                    "ordinal": match.group(1).split("_", 1)[0],
                    "digest": match.group(1).rsplit("_", 1)[1],
                    "fields": _entry_fields(match.group(2)),
                }
                for match in _MAP_ENTRY_RE.finditer(map_m.group(2))
            ]
        blocks.append(
            {
                "local": local,
                "for_each": f"local.{map_name}",
                "group": _search_one(body, r'device_group = \{\s*name = "([^"]+)"')
                or _search_one(body, r'vsys = \{\s*name = "([^"]+)"'),
                "where": _search_one(body, r'where = "([^"]+)"'),
                "args": re.findall(r"^  ([a-z_][\w]*) = ", body, re.M),
                "body_fields": re.findall(r"      ([a-z_][\w]*) = each\.value\.([a-z_][\w]*)", body),
                "entries": entries,
            }
        )
    return blocks


def check_chain_semantics(blocks: list[dict], resource_type: str, expected: list[tuple[str, list[str]]], msg: str):
    """Assert the printed shape carries the chain: one block per unit, and the key order is the XML order.

    `expected` is one pair per unit, in the order the file prints the units: the location name the block states,
    and that unit's rule names in the order the export lists them. The names are read as the file prints them, so
    the entry side of the pin reads the printed form of the row and not a copy of the name.

    The block reads the map named by the one stem (`rule_data.locals_name`), so the block name, the map name, the
    `.json` form and the `.csv` form are one name; the position anchor is the same for every instance of one block,
    because the apply order comes from the key and not from a per-instance pivot; the ordinals run 1..N inside a
    chain; the printed entry order is the sorted key order, which is the XML order inside a chain; and one block
    holds one unit's rows, so every key's digest half is the digest the block's own location names.
    """
    assert len(blocks) == len(expected), msg
    stem = rule_data.locals_name(resource_type)
    name_field = entry_coverage.name_field(resource_type)
    for block, (group, names) in zip(blocks, expected, strict=True):
        assert block["local"] == stem, f"{msg}: the block name is not the matrix row's stem: {block['local']}"
        assert block["for_each"] == f"local.{stem}", f"{msg}: the block does not read the map named by the stem"
        assert block["group"] == group, msg
        assert block["where"] == "last", msg
        entries = block["entries"]
        assert len(entries) == len(names), f"{msg}: {block['local']} prints {len(entries)} for {len(names)} rules"
        assert [entry["key"] for entry in entries] == sorted(entry["key"] for entry in entries), msg
        assert [entry["ordinal"] for entry in entries] == [
            f"{position:0{rule_data.ORDINAL_WIDTH}d}" for position in range(1, len(names) + 1)
        ], msg
        assert [entry["fields"][name_field] for entry in entries] == [f'"{name}"' for name in names], msg
        assert {entry["digest"] for entry in entries} == {entries[0]["digest"]}, msg


@pytest.fixture(scope="session")
def provider_schemas(tmp_path_factory) -> dict:
    """The panos provider schema block for one type block: both kinds.

    Runs `terraform init` + `terraform providers schema -json` against the provider version declared in the golden
    provider.tf. This is the owner of the skip rule for the schema fixture: the fixture skips only when the
    terraform binary is absent, which is the case on a runner with no terraform. Once the binary is present, a
    failed `terraform init` is a failure, not a skip, so a missing provider cache or an unreachable registry reads
    as a failing run rather than as a pass. `.github/workflows/python-tests.yml` is the CI owner: the job with the
    terraform binary runs the whole test set, so these pins run there.
    """
    if TERRAFORM is None:
        pytest.skip("terraform binary not found")
    source, version = declared_provider()
    workdir = tmp_path_factory.mktemp("panos_provider")
    (workdir / "provider.tf").write_text(
        "terraform {\n"
        "  required_providers {\n"
        "    panos = {\n"
        f'      source  = "{source}"\n'
        f'      version = "{version}"\n'
        "    }\n"
        "  }\n"
        "}\n"
    )
    init = subprocess.run(
        [TERRAFORM, "init", "-backend=false", "-input=false"],
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert init.returncode == 0, f"terraform init failed: {init.stderr[-400:]}"
    schema = subprocess.run(
        [TERRAFORM, "providers", "schema", "-json"],
        cwd=workdir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert schema.returncode == 0, schema.stderr
    data = json.loads(schema.stdout)
    key = next(k for k in data["provider_schemas"] if k.endswith("/panos"))
    return data["provider_schemas"][key]


@pytest.fixture(scope="session")
def provider_schema(provider_schemas) -> dict:
    """The panos provider's resource schemas, keyed by resource type."""
    return provider_schemas["resource_schemas"]


@pytest.fixture(scope="session")
def provider_data_schemas(provider_schemas) -> dict:
    """The panos provider's data source schemas, keyed by data source type (F5.5)."""
    return provider_schemas["data_source_schemas"]


@pytest.fixture(scope="session")
def converter_module():
    """The converter module in the `src/` namespace, read through the import rule (§1.1)."""
    return panorama_to_terraform


@pytest.fixture(scope="session")
def splitter_module():
    """The splitter module in the `src/` namespace, read through the import rule (§1.1)."""
    return split_device_groups


@pytest.fixture(scope="session")
def xml_input_module(converter_module):
    """The shared safe-input module (F3.8) both entry points import.

    Returned after the converter loads, so the module object is the one the
    scripts hold: a test and a script then share one UnsafeInputError class.
    """
    return sys.modules["xml_input"]


@pytest.fixture(scope="session")
def fetch_module(xml_input_module):
    """The F5.2 fetch module as the converter holds it.

    The same module object, so a test and the script share one
    SourceFetchError class and the same parse_bytes reference the door is.
    """
    return sys.modules["source_fetch"]


@pytest.fixture
def make_parser(converter_module, xml_input_module):
    """Return a factory that builds a PanoramaParser bound to a fixture file.

    F5.2: the parser takes a ParsedSource, so the factory reads the fixture
    through the door and hands the contract, not a path.
    """

    def _make(fixture_name: str):
        return converter_module.PanoramaParser(xml_input_module.parse_xml(FIXTURES_DIR / fixture_name))

    return _make


def per_scope_response(request, body: str) -> bytes:
    """One response in the shape the request states: `result` holds the element the path names.

    For an entry read the path names the entry itself, so the tree holds no element at the place level, which is
    the fact the definitions rule cannot read through the walk. Two modules build the predefined content through
    this, so the shape is stated once, in the shared harness (§1.1).
    """
    segments = request.segments()
    held = body if len(segments) == 3 else f"<{segments[0]}>\n{body}</{segments[0]}>\n"
    return (
        '<?xml version="1.0"?>\n<response type="success" code="0">\n<result>\n' + held + "</result>\n</response>\n"
    ).encode()


def api_producer(request, key=None, insecure=False):
    """The committed response for one request, handed by the name `RESPONSES_DIR` holds it under (§1.1).

    A path 2 pin runs the pipeline in process with this producer, so no test calls a network. A request with
    no committed response answers None, so a run reads only the committed set, and the join reads the set the
    run read.
    """
    entry = RESPONSES_DIR / request.cache_name()
    return None if not entry.is_file() else entry.read_bytes()


def path2_run(output_dir, cache_dir, monkeypatch, host: str = "panorama.test") -> tuple:
    """A path 2 run, and the index the join reads for it.

    A path 2 pin cannot use `run_script`, because the injected producer lives in this process, so the run is
    in process and the index is built the way the run order builds it: the tables `parse_associations`
    returned for the response the run read, and the read set the join states.
    """
    monkeypatch.setattr(source_fetch, "network_producer", api_producer)
    monkeypatch.setenv(source_fetch.API_KEY_ENV, "test-key")
    parser = run_pipeline(
        panorama_to_terraform, None, output_dir, ("--source", "api", "--host", host, "--cache-dir", str(cache_dir))
    )
    assert parser is not None, "the run refused the input"
    return parser, api_requests.scope_index(host, parser.parse_associations(), api_requests.membership_lists())


def run_script(module_name, *args: str) -> subprocess.CompletedProcess:
    """Run a tool module as a subprocess. Returns the process result.

    `module_name` is a module name in the `src/` namespace (`docs/ARCHITECTURE.md` §1.1), so the path is
    built once here and every test names the module, not the directory. A path is used as given.
    """
    path = Path(module_name)
    if not path.is_absolute():
        path = SRC_DIR / path
    return subprocess.run(
        [sys.executable, str(path), *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
    )


def run_main(module, argv: list):
    """Run the converter main() in process with the given argv. Returns the exit code.

    F5.2 tests need an in-process run so an injected producer can stand in for the
    network. Console output is redirected, so an in-process run does not fill the
    pytest report.
    """
    saved_argv = list(sys.argv)
    sys.argv = ["panorama_to_terraform.py", *[str(a) for a in argv]]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return module.main()
    finally:
        sys.argv = saved_argv


def run_pipeline(module, fixture_name, output_dir, extra_args: tuple = ()):
    """Run the converter pipeline in process and return the parser it built.

    The F4.4 property scan measures which keys an output reads from a captured object,
    so a test that wants the read record must run the pipeline in process: `run_script`
    runs a subprocess and the record is lost with the process. `main()` builds the
    parser itself, so this helper hooks `PanoramaParser.__init__` to get the instance
    back.

    `extra_args` is appended to argv (F5.4), so a run can declare a source, a host, or a
    scope path. `fixture_name` is None when argv names the source instead of a file.

    Returns None when the run refuses the input before the parse, because no parser
    exists to return. Console output is redirected, so a corpus run does not fill the
    pytest report.
    """
    captured = {}
    original_init = module.PanoramaParser.__init__

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        captured["parser"] = self

    argv = ["panorama_to_terraform.py"]
    if fixture_name:
        argv.append(str(FIXTURES_DIR / fixture_name))
    argv.extend(["--output-dir", str(output_dir)])
    argv.extend(str(arg) for arg in extra_args)

    saved_argv = list(sys.argv)
    module.PanoramaParser.__init__ = init
    try:
        sys.argv = argv
        with contextlib.redirect_stdout(io.StringIO()), contextlib.suppress(SystemExit):
            module.main()
    finally:
        module.PanoramaParser.__init__ = original_init
        sys.argv = saved_argv
    return captured.get("parser")
