"""Resource mapping tests (Epic 2).

resource_mapping.py is the single source of truth for what the converter
produces against the panos provider v2:

- EMITTED_TYPES: the v2 resource types the generator emits. These must
  match the committed goldens exactly and exist in the provider schema.
- REPORT_ONLY_TYPES: PAN-OS config types with no v2 resource; their data
  goes to the manual setup report. A false report-only decision would
  hide a real resource, so every entry must be absent from the schema.
- NOT_EMITTED_TYPES: v2 resource types that exist but the converter
  intentionally does not emit (the body is not parsed, F2.9). A
  not-emitted row must correspond to a type that really exists, so the
  report entry can name the real resource.
"""

import pytest

from conftest import emitted_types
from resource_mapping import EMITTED_TYPES, NOT_EMITTED_TYPES, REPORT_ONLY_TYPES


def test_emitted_types_match_goldens():
    """The table must name exactly the types the goldens emit."""
    golden = emitted_types()
    missing = sorted(golden - EMITTED_TYPES)
    extra = sorted(EMITTED_TYPES - golden)
    assert not missing, f"emitted types with no mapping row: {missing}"
    assert not extra, f"mapping rows for types the goldens do not emit: {extra}"


@pytest.mark.parametrize("rtype", sorted(EMITTED_TYPES))
def test_emitted_type_exists_in_provider(rtype, provider_schema):
    """Every emitted type must be a real provider v2 resource."""
    assert rtype in provider_schema, (
        f"{rtype!r} is emitted but does not exist in the panos provider schema"
    )


@pytest.mark.parametrize("rtype", sorted(REPORT_ONLY_TYPES))
def test_report_only_is_genuinely_absent(rtype, provider_schema):
    """A report-only row must correspond to a type that is really missing.

    Guards against a report-only decision masking a resource that exists
    in v2 (which should have been emitted instead).
    """
    assert rtype not in provider_schema, (
        f"{rtype!r} is marked report-only but exists in the provider schema; emit it"
    )


@pytest.mark.parametrize("rtype", sorted(NOT_EMITTED_TYPES))
def test_not_emitted_is_genuinely_present(rtype, provider_schema):
    """A not-emitted row must name a real provider v2 resource (F2.9).

    The inverse of the report-only absence guard: these types DO exist in
    v2, and the manual setup report names them as the target to configure
    by hand. If a type stops existing, the report entry is wrong and the
    decision should move to report-only.
    """
    assert rtype in provider_schema, (
        f"{rtype!r} is marked not-emitted but does not exist in the provider "
        f"schema; it belongs in REPORT_ONLY_TYPES"
    )
