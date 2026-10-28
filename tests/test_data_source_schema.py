"""F5.5: `DATA_SOURCE_SCHEMA` pinned against the live provider schema.

The table is data, so these tests do not restate it row by row. They compare each
row with the provider schema the `provider_schema` fixture reads, through the two
facts the gate rule for a `data` block needs: whether the type declares `name`, and
the `location` sub-blocks with the fields each declares.

The table is the complete declared shape, not the generator subset `LOCATION_SCHEMA`
is, because `terraform validate` accepts an unknown `location` sub-block and drops it
silently, so the gate rule is the offline check.

The fixture skips when the terraform binary or the provider cache is absent. That is
the decision this feature recorded: no committed schema snapshot, because a snapshot
would be a second copy of the same fact and could drift from the pinned provider
version.

Pins:

- every row names a real data source, and every data source has a row;
- the sub-blocks and fields in a row equal the live shape, with nothing added and
  nothing missing;
- `location` is required for every data source, and `name` is required for every data
  source that declares one (106 rows, and 22 that declare none);
- `LOCATION_SCHEMA` stays inside the data shape for a type in both tables;
- the 126 types that exist in both sets share the shape and the `name` fact, and the
  four types that exist in one set only stay asymmetric (a set fact, not a `name` fact).
"""

import pytest

from resource_mapping import DATA_SOURCE_SCHEMA, LOCATION_SCHEMA


def _fields(value: dict) -> tuple:
    """The attributes a nested block declares, in sorted order."""
    return tuple(sorted(value.get('nested_type', {}).get('attributes', {})))


def _live_shape(schema: dict) -> dict:
    """The live `location` shape for one data source, as {sub-block: fields}."""
    location = schema['block']['attributes'].get('location')
    if not location or 'nested_type' not in location:
        return {}
    return {
        sub_block: _fields(attributes)
        for sub_block, attributes in location['nested_type'].get('attributes', {}).items()
    }


# --- the table against the live schema ---------------------------------------

def test_the_table_covers_every_data_source(provider_data_schemas):
    """No data source is missing from the table, and the table names none that does
    not exist."""
    live = set(provider_data_schemas)
    assert sorted(DATA_SOURCE_SCHEMA) == sorted(live), sorted(
        set(DATA_SOURCE_SCHEMA) ^ live)


@pytest.mark.parametrize('rtype', sorted(DATA_SOURCE_SCHEMA))
def test_a_row_equals_the_live_shape(rtype, provider_data_schemas):
    """The two facts of a row are the live facts: the `name` flag and the shape."""
    declares_name, shape = DATA_SOURCE_SCHEMA[rtype]
    attributes = provider_data_schemas[rtype]['block']['attributes']
    assert declares_name == ('name' in attributes), rtype
    assert shape == _live_shape(provider_data_schemas[rtype]), rtype


def test_location_is_required_for_every_data_source(provider_data_schemas):
    """The gate rule can require `location` because the provider requires it."""
    for rtype, schema in provider_data_schemas.items():
        attributes = schema['block']['attributes']
        assert attributes.get('location', {}).get('required'), f'{rtype} location'


def test_name_is_required_when_the_row_declares_one(provider_data_schemas):
    """A row that declares `name` means a required name, so a block without one is a
    finding."""
    for rtype, schema in provider_data_schemas.items():
        attributes = schema['block']['attributes']
        if 'name' in attributes:
            assert attributes['name'].get('required'), f'{rtype} name'


def test_the_name_counts_and_the_two_sets(provider_data_schemas):
    """128 data sources: 106 declare `name`, 22 do not (the settings, policy, and
    collection shapes). The gate rule must not require a name for the 22."""
    name_rows = sorted(t for t, (declares_name, _shape) in DATA_SOURCE_SCHEMA.items()
                       if declares_name)
    no_name_rows = sorted(t for t, (declares_name, _shape) in DATA_SOURCE_SCHEMA.items()
                          if not declares_name)
    assert len(name_rows) == 106, len(name_rows)
    assert len(no_name_rows) == 22, len(no_name_rows)
    live_no_name = sorted(
        t for t, schema in provider_data_schemas.items()
        if 'name' not in schema['block']['attributes'])
    assert no_name_rows == live_no_name


# --- the table against the generator's location rule -------------------------

def test_location_schema_stays_inside_the_data_shape(provider_data_schemas):
    """A sub-block and field the generator can write must be one the data shape
    declares, so a read-through block and a resource block cannot disagree."""
    for rtype, scopes in LOCATION_SCHEMA.items():
        if rtype not in DATA_SOURCE_SCHEMA:
            continue
        shape = DATA_SOURCE_SCHEMA[rtype][1]
        for sub_block, fields in scopes.items():
            assert sub_block in shape, f'{rtype}.{sub_block}'
            assert tuple(sorted(fields)) == shape[sub_block], f'{rtype}.{sub_block}'


def test_the_shared_types_mirror_the_resource_shape(provider_schema,
                                                    provider_data_schemas):
    """126 types exist in both sets, and for those the data row equals the resource
    shape on both facts. That is why the data table can be the complete shape while
    `LOCATION_SCHEMA` stays a generator subset.
    """
    shared = sorted(set(provider_schema) & set(provider_data_schemas))
    assert len(shared) == 126, len(shared)
    for rtype in shared:
        declares_name, shape = DATA_SOURCE_SCHEMA[rtype]
        attributes = provider_schema[rtype]['block']['attributes']
        assert ('name' in attributes) == declares_name, rtype
        assert shape == _live_shape(provider_data_schemas[rtype]), rtype
        live_resource = {
            sub_block: _fields(value)
            for sub_block, value in attributes['location']['nested_type']['attributes'].items()
        }
        assert shape == live_resource, rtype


def test_the_name_level_asymmetries_stay_asymmetries(provider_schema,
                                                      provider_data_schemas):
    """Four types are named by one set only, so the gate cannot assume the two tables
    mirror each other: two resources have no data source, and two data sources have no
    resource. A `data` block for a resource-only type is a gate finding, and a resource
    name fact cannot be read from the data table for a data-source-only type."""
    resource_only = sorted(set(provider_schema) - set(provider_data_schemas))
    data_only = sorted(set(provider_data_schemas) - set(provider_schema))
    assert resource_only == ['panos_certificate_import', 'panos_virtual_router_interface']
    assert data_only == ['panos_certificate', 'panos_predefined_dlp_file_type']
    for rtype in resource_only:
        assert rtype not in DATA_SOURCE_SCHEMA, rtype
    for rtype in data_only:
        assert rtype not in provider_schema, rtype
        assert DATA_SOURCE_SCHEMA[rtype][0], rtype
