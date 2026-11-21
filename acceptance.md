# Piece F5.6 acceptance criteria — the state-scan comparison table

Current task: build the comparison table the state scan reads — the parse key the coverage matrix row
names, and the attribute name the pinned provider schema declares for the same value — as data in
`src/state_coverage.py`, and pin it in `tests/test_state_coverage.py`.

## Criterion 1 — the table content is a measurement, not a choice

The table is built from a measurement per matrix row type against the pinned provider schema
(`tests/conftest.py::provider_schema`, the provider the golden `provider.tf` declares). The measurement
is:

- run the pipeline on the row's own fixture;
- read the resource block the run wrote for the row's entry, and read its fields at the block's own
  level through the gate's one field reader (`sanity_checks.blocks`, `Block.fields`);
- pair each printed field name with the row property whose value produced it, so the pair is what the
  run prints, not a name a person picked;
- keep a pair only when the printed name is an attribute the pinned schema declares at the block's top
  level for the row's type, because `state_properties` reads only top-level state attributes, so a name
  inside a nested level is not a value the scan can compare;
- keep a pair only when the printed value is the same data the parse key holds, so the two sides hold
  the pair in the same shape; a printed value that answers for more than one parse key is not a pairing.

A table row exists only where the two names differ: the same-name rule already covers a property the
table has no row for, so a row for an equal name would state nothing.

The pin runs the same measurement, not a copy of the table. `tests/conftest.py` owns the skip rule: the
pin skips only when the terraform binary is absent, and a failed `terraform init` is a failure.

## Criterion 2 — the scan reads the mapping only through the table

`state_coverage.state_name_for` is the one lookup the drift scan uses. Where the table has a row for a
property, the scan compares the parse key with the state attribute named by that row. Where the table
has no row, the same-name rule stands unchanged. No `src/` module holds a second parse-key-to-attribute
mapping, and the pin measures that across the `src/` set.

## Criterion 3 — a finding names a mapped pair the same-name rule cannot reach

A drift finding for a mapped pair is grounded by committed fixtures: the run side from the row's fixture,
the state side from `tests/fixtures/state_workspace.json`. The state attribute name in the fixture is a
name the pinned schema declares, so the pair is a schema fact and not a fixture wording. Under the
same-name rule the scan compares nothing for that entry, so the finding only exists because of the
table.

## Criterion 4 — one pin per fact, in the module that owns the rule

- the table against the live schema and against the run's printed field names: one pin;
- a drift finding that names a mapped pair: one pin;
- the same-name rule where the table has no row: one pin;
- no second mapping rule in `src/`: one pin;
- the drift line for a mapped pair names both names: one pin.

All pins are in `tests/test_state_coverage.py`, which owns the state scan rules. No test module imports
another test module; shared facts come from `tests/conftest.py`.

## Criterion 5 — the report line shape

The ownership line shape is unchanged. The drift line keeps its shape and names the property; for a
mapped pair it names both sides, so the operator can see the two names the finding compared. A property
the table has no row for prints as one name, as before.

## Criterion 6 — the documents

`docs/ARCHITECTURE.md` §3.2 is the owner document for the drift rule and carries the decision and the
measurement. The wrong example in that paragraph — `panos_address` declares `tags`, so `tags` and `tag`
is not a schema fact — is removed, and the measurement record states what was measured. The closed
backlog entry is removed. `to-do.md` and `agent-status.md` carry the current state. No test count in a
document, no metaphor, no emoji, ASD-STE100 wording.

## Criterion 7 — the gate, single-threaded, with measured counts

`ruff check .`, `ruff format --check .`, `python3 tools/check_documents.py`, `python3 -m pytest`, all
single-threaded. The pin counts are read from the per-module collection counts, because `pyproject.toml`
sets `addopts = "-q"`.

## Measured result

The piece is landed at commit `43d6101`. Criterion 1, measured 2026-11-21 against provider v2.0.14 (`PaloAltoNetworks/panos ~> 2.0.14`, read through
`tests/conftest.py::provider_schema`): over the 42 matrix rows, 26 types reach a pair, no printed field
answers for more than one parse key, and 16 rows reach no field at the block's own level. Four pairs name
the parse key and a different attribute name, and those are the four table rows: `static_members` for
`static` on `panos_address_group`, and `authentications` for `hash`, `dh_groups` for `dh_group` and
`encryptions` for `encryption` on `panos_ike_crypto_profile`. Every table key is a property of its own row
and every table name is a top-level attribute the schema declares for that same type.

Criterion 2: `state_name_for` is the only lookup `drift_properties` reads, and the scan over the `src/` set
finds no module-level dict that pairs a parse key with an attribute name it is not named under other than
the table. The pin asserts the hit set is not empty, so it measures the table rather than an absence.

Criterion 3: the committed state document holds `panos_address_group` entry `Web-Servers`, read under
`static`, the name the schema declares, against the run side `static_members` from
`tests/fixtures/address_groups.xml`. The state value differs, so the finding exists only because of the
table. `panos_ike_crypto_profile` cannot be the grounded pair, because `LOCATION_SCHEMA` declares no `shared`
scope for it, so a state entry of that type cannot be keyed in the shared workspace the scan reads.

Criterion 4: the six pins are group 7 of `tests/test_state_coverage.py` — the measured pairs, the parse key
printed under four names, the mapped pair read through the state document, the same-name rule where the
table has no row, the scan reading the mapping only through the table, and the drift line for a mapped pair.

Criterion 5: the drift line prints `static_members as static (["Web-Server-1", "Web-Server-2"] vs
["Web-Server-1"])` for the mapped pair, and the one name `members` for a property the table has no row for.

Criterion 6: `docs/ARCHITECTURE.md` §3.2 carries the decision, the measurement and the two shapes the
measurement cannot state as one name; the `tags`/`tag` example is removed, because `panos_address` declares
`tags`, the same name the parse key has. The closed backlog entry is removed from `backlog.md`, and the two
measurement gaps are recorded there. `README.md` names the comparison table in the `tests/test_state_coverage.py`
entry. `tools/check_documents.py` reports no finding.

Criterion 7, single-threaded: `ruff check .` clean at `py310`, `ruff format --check .` clean on the 104
Python files, `python3 tools/check_documents.py` reports no finding, and `python3 -m pytest` passes 1,738
pins with the same 4 skip for the missing `tflint` binary — 1,742 pins in 53 test modules, in 243.32 s on the
recorded run. `terraform` is present, so the pins that read the live provider schema ran, and the 4 skips are
the `tflint` pins in `tests/test_sanity_gate.py`. Read through the per-module collection counts: 1,736 pins in
53 modules before the piece, 1,742 here, so the piece adds six pins, all in `tests/test_state_coverage.py`,
which collects 24 before and 30 here. The measurement pin runs the pipeline for every matrix row, so the gate
reads 42 fixtures and one provider schema; run-to-run time varies, and the recorded runs of this tree measured
243.32 s and 265.73 s. The import rule reads clean: no test module imports another test module.
