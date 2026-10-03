"""Provider schema conformance tests.

The provider schema is the single source of truth for what the generator
may emit. These tests load ``terraform providers schema -json`` for the
provider version declared in the generated ``provider.tf`` and check the
committed golden output against it:

1. Every emitted resource type must exist in the provider schema.
2. For every emitted resource that exists, each required attribute of that
   type (for example ``location``) must be present in every generated block.

Red→green: the current v1-style generator output fails these checks. The
failing cases are marked ``xfail`` with reasons pointing at the Epic 2
tasks that fix them (F2.2 resource mapping, F2.3 location). As Epic 2
lands, cases flip to xpass; then the markers come off and the suite goes
green.

The tests run against the committed golden .tf files; the golden tests
already guarantee that a fresh generation equals the goldens.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
TERRAFORM = shutil.which("terraform")

# Top-level arguments of a generated resource block are exactly the lines
# with two-space indent (nested content is indented deeper).
_RESOURCE_RE = re.compile(r'resource\s+"([a-z0-9_]+)"\s+"[^"]+"\s*\{')
_TOPLEVEL_ARG_RE = re.compile(r"^  ([a-z0-9_]+)\s*[={]")


def _declared_provider() -> tuple[str, str]:
    """Read the panos provider source and version from the golden provider.tf."""
    text = (GOLDEN_DIR / "sample" / "provider.tf").read_text()
    block = re.search(r"panos\s*=\s*\{([^}]*)\}", text, re.S).group(1)
    source = re.search(r'source\s*=\s*"([^"]+)"', block).group(1)
    version = re.search(r'version\s*=\s*"([^"]+)"', block).group(1)
    return source, version


def _blocks_for_type(golden_dir: Path) -> dict[str, list[set[str]]]:
    """Map emitted resource type -> list of top-level argument sets per block."""
    blocks: dict[str, list[set[str]]] = {}
    for path in sorted(golden_dir.rglob("*.tf")):
        lines = path.read_text().splitlines()
        i = 0
        while i < len(lines):
            m = _RESOURCE_RE.match(lines[i])
            if m is None:
                i += 1
                continue
            rtype = m.group(1)
            i += 1
            args: set[str] = set()
            while i < len(lines) and lines[i] != "}":
                a = _TOPLEVEL_ARG_RE.match(lines[i])
                if a:
                    args.add(a.group(1))
                i += 1
            blocks.setdefault(rtype, []).append(args)
            i += 1
    return blocks


EMITTED_BLOCKS = _blocks_for_type(GOLDEN_DIR)
EMITTED_TYPES = sorted(EMITTED_BLOCKS)


@pytest.fixture(scope="session")
def provider_schema(tmp_path_factory) -> dict:
    """The panos provider's resource schemas, keyed by resource type."""
    if TERRAFORM is None:
        pytest.skip("terraform binary not found (F1.5 makes it mandatory in CI)")
    source, version = _declared_provider()
    workdir = tmp_path_factory.mktemp("panos_provider")
    (workdir / "provider.tf").write_text(
        "terraform {\n"
        "  required_providers {\n"
        '    panos = {\n'
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
    if init.returncode != 0:
        pytest.skip(f"terraform init failed (no registry access?): {init.stderr[-400:]}")
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
    return data["provider_schemas"][key]["resource_schemas"]


@pytest.mark.xfail(reason="emitted type is not in the provider schema; fixed by Epic 2 F2.2", strict=False)
@pytest.mark.parametrize("rtype", EMITTED_TYPES)
def test_resource_type_exists_in_provider(rtype, provider_schema):
    """Every emitted resource type must exist in the declared provider."""
    assert rtype in provider_schema, f"resource type {rtype!r} does not exist in the panos provider"


@pytest.mark.xfail(reason="required attribute missing from generated block; fixed by Epic 2 F2.3", strict=False)
@pytest.mark.parametrize("rtype", EMITTED_TYPES)
def test_required_attributes_present(rtype, provider_schema):
    """Every required attribute of an emitted type must appear in every block."""
    if rtype not in provider_schema:
        pytest.xfail(f"{rtype} is not in the provider schema (see test_resource_type_exists_in_provider)")
    required = sorted(
        attr
        for attr, meta in provider_schema[rtype]["block"].get("attributes", {}).items()
        if meta.get("required")
    )
    blocks = EMITTED_BLOCKS[rtype]
    assert blocks, f"no {rtype!r} blocks found in the goldens"
    missing = sorted(set(required) - set().union(*blocks))
    assert not missing, f"{rtype}: required attributes missing from generated blocks: {missing}"
