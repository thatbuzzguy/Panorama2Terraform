# Acceptance criteria — the certificate containers (task for this commit)

Scope: the two `CONTAINER_TABLE` rows, the two parse methods, the two emitters, and the
goldens regenerated from a real run. The gate rule for a certificate block is the next
task, so this commit adds no gate code.

## 1. The tables state the facts the emitter prints

1.1 `CONTAINER_TABLE` holds one row per parse method: `parse_certificates` reading
`certificate` and `parse_certificate_profiles` reading `certificate_profile`. Both rows are
`emitted` and name the provider type in the note, because the property scan reads a matrix
row only for an emitted row (`entry_coverage.matrix_row_for`).

1.2 `COVERAGE_MATRIX` holds one row per emitted type, so both certificate types gain a row,
and each row names a fixture entry, an emitter, an output file, and the properties the
emitter reads. A row's properties are the fields the emitter reads from the captured object,
in the print order.

1.3 The field names and shapes are the live provider facts, measured 2026-11-05 against
provider 2.0.14 (`terraform providers schema -json`): `panos_certificate_import` declares
`name`, `location`, `local`; `local` is one object with the `pem` and `pkcs12` sub-shapes, and
`terraform validate` refuses a `local` stating both, so the choice is stated by presence.
`panos_certificate_profile` declares 15 attributes, none sensitive.

1.4 `CERTIFICATE_SHAPE` is the table that owns these shapes, so the emitter prints through it
and a gate rule can read the same rows. One reader serves every shape table, so no method
writes a field name of its own.

1.5 The two `sensitive` facts (`private_key`, `passphrase`) are `REFERENCE_ONLY` rows in
`VALUE_VARIABLES`, so the block prints the variable reference and no generated file states the
value (`tests/test_robustness.py` rule).

1.6 `LOCATION_SCHEMA` holds one row per emitted type, and each row lists only the sub-blocks
the location rule can reach. The profile row holds `template` only: the shared sub-block is
reached only inside the device-group branch, and the profile row declares no device group, so
stating `shared` would be a fact the tool cannot use. The tool prints the `Shared` template
placeholder for a profile entry the export places in a device group, and the test pins what the
tool prints.

1.7 `panos_certificate_import` is the first emitted type with no data source, so the name rule
needs a fact source for a type `DATA_SOURCE_SCHEMA` has no row for. One table states it, and the
test pins it against the live schema.

1.8 `entry_coverage.name_field` stays the one rule for the field that carries an entry name, and
it answers through that table for a resource-only type.

## 2. The parse methods

2.1 Each method marks every entry it reads, and reads only the fields its row states.

2.2 An entry with no name is skipped, with the reason.

2.3 A certificate entry that states no `local` sub-shape is still an object the run can place:
`name` and `location` are the only facts the provider requires, so the entry is emitted.

## 3. The emitters

3.1 One resource block per entry, in the row's field order, with the location block.

3.2 `local` prints as the one sub-shape the export states; the alternative the export does not
state prints nothing.

3.3 A `sensitive` field prints as the variable reference named by the entry that holds it (§5),
never as its value.

3.4 The `certificate` list inside a profile entry prints as the list shape the provider declares
(one object per entry the export holds), because `terraform validate` refuses a single object.

3.5 Each emitter writes one file per unit that has content, in the order the run read it.

## 4. The corpus and the goldens

4.1 `tests/fixtures/certificates.xml` holds the entries the emitter reads, each in a scope its
row's type can place (vsys for an import entry, template for a profile entry), and carries every
declared property with a non-empty value, so the property scan measures every field the row states.

4.2 The kitchen-sink record holds a certificate entry and a profile entry, so the golden case
exercises both generator paths. The goldens are the bytes a real run wrote, regenerated from that
run and never hand-edited.

4.3 The pins that move move in the same commit: the container findings, the fixture counts, the
value-table pins, the name-asymmetry pin, the ngfw pin, and the reference-name pin. A pin states
the measured fact, not a guess.

4.4 `ruff check .` is clean and `python3 -m pytest` passes.

## 5. What this commit does not do

5.1 No gate rule for a certificate block. The emitter prints a shape a gate can read: field names
as the provider spells them, values in the shape the table states, the choice by presence.

5.2 The EDL `certificate_profile` field stays a plain string, so it records no reference edge. A
read-through data block cannot answer a name for a type whose data row declares no `name` field,
and `panos_certificate_profile` is not such a type — but the EDL site does not resolve names, so
the reference rule cannot reach it. This stays a finding in `backlog.md`.

## Result (measured 2026-11-05)

All criteria hold. `ruff check .` is clean and `python3 -m pytest` passes 1518 tests.

1.1 Both `CONTAINER_TABLE` rows are `emitted` and name the provider type. The profile row path is the
input's spelling `certificate-profile`, because the scan reads the row path off the input, and the parse
method states the table path `certificate_profile`. The profile's `certificate` list holds one entry per
object, so the objects are a `nested-block` row under the profile row, and the row path holds the `entry`
segment the profile entry is; without it the single-segment `certificate` row would answer for the object.

1.2 Both `COVERAGE_MATRIX` rows hold. The profile row declares 16 properties: the 13 fields the emitter
reads from the entry, plus the 3 fields it reads for the objects inside its `certificate` list, which the
property scan measures against the profile row through the nested row. The import row declares `local` only.

1.4 `CERTIFICATE_SHAPE` is the shape owner for both emitters, and `tests/test_coverage_matrix.py::_shape_table_grounding`
reads the certificate table branch. `CERTIFICATE_TABLE` carries `root='certificate'`, so the reference-name walk
in `tests/test_variables.py` names no container.

1.5 `VALUE_VARIABLES` holds the two `REFERENCE_ONLY` rows, and the goldens print the reference.

1.7 `RESOURCE_NAME_FIELDS` holds the two resource-only types, and
`tests/test_data_source_schema.py::test_the_name_fact_for_a_resource_only_type` pins it against the live schema;
`test_the_certificate_table_is_the_live_shape` pins `CERTIFICATE_SHAPE` on the field set and the `sensitive` flags,
and on `selects` for the `one_of` row.

2.3 The record's certificate entry states `local`, and the fixture's profile entry states every declared field.

3.1–3.5 Both emitters print through the table, in the row's order, with the location block; the two files are
`certificates.tf` and `certificate_profiles.tf`, one `UnitText` each, so neither overwrites the other.

4.2 Goldens that moved, from one real run on `tests/fixtures/kitchen_sink.xml`:
`tests/golden/kitchen_sink/vsys1_78d8e4bc/certificates.tf` (new),
`tests/golden/kitchen_sink/fw_template_00a08cdc/certificate_profiles.tf` (new), and
`tests/golden/kitchen_sink/vsys1_78d8e4bc/variables.tf` (the run declared `var.vsys_cert`, the §5 name of the
entry that holds the two `sensitive` fields).

4.3 Pins that moved in this commit: `tests/test_container_coverage.py::EXPECTED_FINDINGS` and the entry-phrasing
pin (the record's certificate entry is covered); the fixture counts in `tests/test_build_kitchen_sink.py`
(68 accepted, 67 read, 3 skipped, 17 comments, 13 names the record holds alone); the reference-only name set and
the pinned table in `tests/test_site_data.py`, plus the golden file-name pin (five files carry a device location)
and the declaration-set clause; `tests/test_variables.py::_reference_names`, which walks both tables through
`ShapeTable.root`; `tests/test_multi_vsys_location.py` ngfw pin; `tests/test_data_source_schema.py` (two new pins);
and `tests/test_coverage_matrix.py` grounding branch. No pin was weakened.

5.1 No gate code was added. `tests/test_edge_cases.py` and the EDL golden are unchanged, so the EDL decision is a
finding, not a change.
