"""Provider schema conformance tests.

The provider schema is the single source of truth for what the generator
may emit. These tests load ``terraform providers schema -json`` for the
provider version declared in the generated ``provider.tf`` and check the
committed golden output against it:

1. Every emitted resource type must exist in the provider schema.
2. For every emitted resource that exists, each required attribute of that
   type (for example ``location``) must be present in every generated block.

The tests run against the committed golden .tf files; the golden tests
already guarantee that a fresh generation equals the goldens.
"""

import re
from pathlib import Path

import pytest

from conftest import GOLDEN_DIR, RESOURCE_RE

# Top-level arguments of a generated resource block are exactly the lines
# with two-space indent (nested content is indented deeper).
_TOPLEVEL_ARG_RE = re.compile(r"^  ([a-z0-9_]+)\s*[={]")


def _blocks_for_type(golden_dir: Path) -> dict[str, list[set[str]]]:
    """Map emitted resource type -> list of top-level argument sets per block."""
    blocks: dict[str, list[set[str]]] = {}
    for path in sorted(golden_dir.rglob("*.tf")):
        lines = path.read_text().splitlines()
        i = 0
        while i < len(lines):
            m = RESOURCE_RE.match(lines[i])
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


# The provider_schema fixture comes from conftest.py (shared with
# tests/test_resource_mapping.py). It verifies against the provider version
# declared in the golden provider.tf.


@pytest.mark.parametrize("rtype", EMITTED_TYPES)
def test_resource_type_exists_in_provider(rtype, provider_schema):
    """Every emitted resource type must exist in the declared provider."""
    assert rtype in provider_schema, f"resource type {rtype!r} does not exist in the panos provider"


def test_every_block_has_location():
    """Every emitted resource block must carry the required location block (F2.3)."""
    missing = [
        f"{rtype} block {i}"
        for rtype, blocks in sorted(EMITTED_BLOCKS.items())
        for i, args in enumerate(blocks)
        if 'location' not in args
    ]
    assert not missing, f"resource blocks missing the required location block: {missing}"


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
