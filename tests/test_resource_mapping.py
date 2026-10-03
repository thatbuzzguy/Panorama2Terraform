"""Resource mapping tests (F2.2).

resource_mapping.py is the table that maps every type the generator emits
today to its real provider-v2 home (or None when v2 has no equivalent).
The F2.4 emitter rewrite consumes it. These tests verify the table itself
against the live provider schema (v2.0.14, per the golden provider.tf):

1. Completeness: the mapping covers exactly the types emitted by the
   committed goldens. A missing row would let an unmapped type through.
2. Targets: every non-None target exists in the provider schema.
3. Report-only: every None entry is genuinely absent from the schema. A
   false None would hide a real resource behind the migration report.
"""

import pytest

from conftest import emitted_types
from resource_mapping import RESOURCE_MAPPING

EMITTED = emitted_types()
MAPPING_KEYS = set(RESOURCE_MAPPING)
MAPPED = sorted((old, new) for old, new in RESOURCE_MAPPING.items() if new is not None)
REPORT_ONLY = sorted(old for old, new in RESOURCE_MAPPING.items() if new is None)


def test_mapping_covers_every_emitted_type():
    """The mapping must name exactly the types the goldens emit."""
    missing = sorted(EMITTED - MAPPING_KEYS)
    extra = sorted(MAPPING_KEYS - EMITTED)
    assert not missing, f"emitted types with no mapping row: {missing}"
    assert not extra, f"mapping rows for types the goldens do not emit: {extra}"


@pytest.mark.parametrize("old_type, target", MAPPED, ids=[f"{o}->{t}" for o, t in MAPPED])
def test_mapped_target_exists_in_provider(old_type, target, provider_schema):
    """Every non-None mapping target must be a real provider v2 resource."""
    assert target in provider_schema, (
        f"mapping target {target!r} (for {old_type!r}) does not exist in the panos provider schema"
    )


@pytest.mark.parametrize("old_type", REPORT_ONLY, ids=REPORT_ONLY)
def test_report_only_is_genuinely_absent(old_type, provider_schema):
    """A report-only row must correspond to a type that is really missing.

    Guards against a report-only decision masking a resource that exists in
    v2 (which should have been mapped instead).
    """
    assert old_type not in provider_schema, (
        f"{old_type!r} is marked report-only but exists in the provider schema; map it to a real target"
    )
