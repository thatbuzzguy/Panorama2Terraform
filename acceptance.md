# Acceptance — measure the certificate types against the pinned provider schema

Piece 1 of the certificate feature. This piece measures; it writes no code and no test.

## Measurement

Measured 2026-11-05 against provider 2.0.14 with Terraform v1.16.2, through `terraform init` +
`terraform providers schema -json` — the same door `tests/conftest.py::provider_schemas` runs. The two
choice facts are read from `terraform validate` on hand-written blocks in a scratch directory; no scratch
file is committed.

### `panos_certificate_import` — resource only, no data source

- Attributes: `local`, `location`, `name`. Required: `name`, `location`.
- No attribute at the block's own level is `sensitive`. The three `sensitive` facts are inside the `local`
  object: `local.pem.private_key`, `local.pem.passphrase`, `local.pkcs12.passphrase`.
- `local` is an object (the schema states it as `single`) with two sub-shapes: `pem` (`certificate`,
  `passphrase`, `private_key`) and `pkcs12` (`certificate`, `passphrase`). `certificate` is required inside
  each, so a block cannot print the key reference alone. `terraform validate` refuses a `local` that states
  both `pem` and `pkcs12`, so `local` is a choice level and `selects` is the one place a row states it
  (`docs/ARCHITECTURE.md` §4.9, the F7.12 rule).
- `location` sub-blocks: `panorama` (`panorama_device`), `template`, `template_stack`,
  `template_stack_vsys`, `template_vsys`, `vsys`. It declares no `device_group` and no `shared`.

### `panos_certificate_profile` — resource and data source, and the two shapes are identical

- Attributes (15): `block_expired_certificate`, `block_timeout_certificate`,
  `block_unauthenticated_certificate`, `block_unknown_certificate`, `certificate`,
  `certificate_status_timeout`, `crl_receive_timeout`, `domain`, `location`, `name`,
  `ocsp_exclude_nonce`, `ocsp_receive_timeout`, `use_crl`, `use_ocsp`, `username_field`.
  Required: `name`, `location`. No field is `sensitive`.
- `certificate` is a list of objects (`name` required, `default_ocsp_url`, `ocsp_verify_certificate`,
  `template_name`); `terraform validate` refuses a single object there, so the emitter must print the list
  shape. `username_field` is an object (`subject`, `subject_alt`). The rest are leaf fields: seven booleans,
  three numbers, `domain` as a string.
- `location` sub-blocks: `panorama` (no field), `shared` (no field), `template`, `template_stack`,
  `template_stack_vsys`, `template_vsys`. It declares no `device_group` and no `vsys`.

### `panos_certificate` — data source only

Confirmed: no resource exists for it. 19 attributes, required `name` and `location`, and no attribute is
`sensitive` — the data source's `private_key` is not marked sensitive, so the §11 rule does not reach it.
`location` sub-blocks: `panorama` (no field), `template`, `template_stack`, `template_stack_vsys`,
`template_vsys`, `vsys`; no `shared`, no `device_group`.

### Set facts re-measured

128 resources, 128 data sources. The resource-only set is `panos_certificate_import` and
`panos_virtual_router_interface`; the data-source-only set is `panos_certificate` and
`panos_predefined_dlp_file_type`. `panos_certificate_profile` is one of the 126 types in both sets, and its
data row equals its resource row.

## What the code states today

Read from `src/resource_mapping.py` and the tests, as the code stands:

- `LOCATION_SCHEMA` has no row for either certificate type. `DATA_SOURCE_SCHEMA` has rows for
  `panos_certificate` and `panos_certificate_profile`, and no row for `panos_certificate_import`, which is
  correct because no data source exists for it.
- Neither certificate type is in `EMITTED_TYPES` or in `NOT_EMITTED_TYPES`.
- `VALUE_VARIABLES` has no row for `private_key` or `passphrase`, so the shape rule has no row for a
  `sensitive` field inside the `local` object.
- `tests/test_container_coverage.py::EXPECTED_FINDINGS` keeps
  `('device-group/entry/certificate', 46, 1)`.
- `tests/fixtures/unknown_containers.xml` carries one certificate entry (`edge-cert`, line 47) with
  `description` only. `description` is an attribute neither certificate type declares, so no output can read
  it, and the entry carries no `profile-name`.

## Facts the measurement contradicted

Corrected in `backlog.md`, which is the owner document for a provider fact no table row covers today:

- `panos_certificate_profile` is not in `LOCATION_SCHEMA`. It is in `DATA_SOURCE_SCHEMA`.
- The recorded profile attribute list omits `ocsp_exclude_nonce` and `ocsp_receive_timeout`, and states
  `certificate` and `username_field` as fields when the schema states them as objects.
- The recorded `sensitive` list omits `local.pkcs12.passphrase`.

## What the next pieces must decide

1. The profile row. Measured: every field the profile declares is a leaf field or a small object, so a parse
   method can read the whole entry. The reason `NOT_EMITTED_TYPES` exists — a partial object would create a
   misconfigured object — does not hold for this type, so the row can be `emitted`. It needs a
   `LOCATION_SCHEMA` row, and the location rule must be read first: `location_data` reaches `shared` only
   inside the `device_group` branch, so a row that declares `shared` without `device_group` prints the
   `Shared` template placeholder instead of `shared = {}`.
2. The location for a certificate entry. No certificate type declares `device_group`, so an entry the export
   places in a device group has no location the emitter can print. The fixture entry must move to a scope the
   type can carry (`template`, `template_stack`, `template_vsys`, `template_stack_vsys`, `vsys`, or
   `panorama`), or the row stays `report` with that reason, and `EXPECTED_FINDINGS` keeps the finding.
3. `VALUE_VARIABLES` needs a `REFERENCE_ONLY` row for `private_key` and for `passphrase`; the two pins in
   `tests/test_site_data.py` that read the table move in the same commit.
4. The `local` choice: the row states `pem` and `pkcs12` as `selects`, and the gate reads the choice at the
   level the walk enters.
5. The `profile_name` pin can be written only after a parse method reads the `certificate` container and the
   fixture entry carries `profile-name`; the pin must run the pipeline, not build a row by hand. Recommend a
   parse method for `certificate` and for `certificate/profile`, and a fixture entry that carries the fields
   the emitter reads, because a captured field no output reads is a finding.
6. Decide whether `certificate_profile` in an EDL sub-shape prints as a reference to the emitted profile
   block. If it does, `tests/golden/kitchen_sink/shared_45ca31c3/external_lists.tf` changes from a real run.

## Rules this must keep

- A document explains a table and never restates it row by row, so the measurement for a type no table row
  covers is recorded in `backlog.md`.
- No new table, no scratch file committed, no code change in this piece.
- `ruff check .` is clean, and `python3 -m pytest` passes.

## Result

Met, 2026-11-05. `ruff check .` is clean and `python3 -m pytest` passes.
