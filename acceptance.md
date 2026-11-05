# Acceptance — the credential rule single statement

## Measurement

Measured 2026-11-04 against provider 2.0.14 through `terraform providers schema -json`, read through
`tests/conftest.py::provider_schemas` (the provider version the golden `provider.tf` declares). Measured on the
`provider_config_block`... the schema key is `provider`, so the test reads `provider_schemas['provider']['block']`:

- 16 arguments, and none is required. The measured set is `additional_headers`, `api_key`, `api_key_in_request`,
  `auth_file`, `config_file`, `hostname`, `multi_config_batch_size`, `panos_version`, `password`, `port`,
  `protocol`, `sdk_log_categories`, `sdk_log_level`, `skip_verify_certificate`, `target`, `username`.
- Two arguments are `sensitive`: `api_key` and `password`. `hostname` and `target` are not.
- A block that states no required argument is a complete block, so the generated block can state only the facts
  the run names, and nothing else.
- The provider docs state `api_key` as the alternative to `username` plus `password`, read from the environment as
  `PANOS_API_KEY` — the same name `source_fetch.API_KEY_ENV` uses. So one credential fact, one environment name,
  and the pair is an alternative path the codebase does not take.

## The statement (one statement, stated once)

Owner: `docs/CODEBASE_ASSEMBLY.md` §11. `docs/ARCHITECTURE.md` §3 links to it and keeps only what the fetch layer
can enforce on its own (argv, the cache name), so no document states the credential rule twice.

1. The credential is the API key. The run takes it from the environment, and the codebase takes it from the same
   environment at plan time (`PANOS_API_KEY`), which the provider reads itself. A run writes no credential pair,
   and no generated file states a credential value.
2. The host is a site fact, not a credential: the measured schema marks `api_key` and `password` sensitive, and
   `hostname` not. The run names the host as a variable and holds no value for it, because no export states the
   host the run read, so it is the same shape as `target`: `operator_supplied`.
3. So `variables.tf` declares only what the run names — the host name, the site values, the reference-only names,
   and the facts the tool cannot read — and `provider.tf` prints the host through the variable the run declares and
   states no credential argument.

## What the code must do

1. `resource_mapping.VALUE_VARIABLES` stays the single shape owner for the provider block arguments, so `hostname`
   gains an `operator_supplied` row beside `target`, and `naming.py` is the only naming rule for it.
2. `generate_provider_config` prints the host through `printed_value`, so the argument name is the §5 rule applied
   to the row, and no name list decides it. It prints `target` only for a unit that names a device (unchanged).
3. `generate_variables` declares the host through the same held-name path as `target`, so the header states no
   `panos_*` name list and each description follows its shape word, not a name.
4. The generated `provider.tf` comment names `PANOS_API_KEY` as the environment the provider reads, so the block
   states the statement in the file it writes; the generated `variables.tf` header states that a credential is not
   a declared variable.

## Pins

1. `tests/test_variables.py`: the declaration set is the site values plus the names the run holds (the
   `operator_supplied` rows) plus the reference names — no credential pair. The provider-block pin reads the block
   through the table: its arguments are the `operator_supplied` rows the run names for that unit, so the `panos_`
   prefix exception in the sensitive pin is gone.
2. `tests/test_variables.py`: the block prints the host for every unit, through `naming.variable_name('hostname')`,
   so a declaration and its consumer are in the same unit directory (§14).
3. `tests/test_variables.py`: no argument the measured schema marks `sensitive` is printed in a generated provider
   block, read through `provider_schemas`, and the environment name the generated block names is
   `fetch_module.API_KEY_ENV`, so one statement names one environment variable in both layers.
4. `tests/test_variables.py` group 1 names the table row for `hostname`, so `tests/test_site_data.py` reads the
   provider arguments as data (`test_the_table_covers_every_field_the_location_can_state`,
   `test_only_the_device_field_maps_to_a_variable`, `test_the_table_holds_no_property`).
5. `tests/test_source_fetch.py` keeps the fetch half: the key comes from the environment, never argv, never the
   cache name, never a generated file. `tests/test_robustness.py::test_a_parsed_secret_never_reaches_a_generated_file`
   keeps the no-secret half, and `tests/test_provenance.py` keeps the provenance rule (the record names the host and
   the scope, never the credential).
6. The goldens move, and only from a real run: `provider.tf` and `variables.tf` in all four cases.

## Rules this must keep

- The `variables` gate rule: every declaration has a `var.` consumer, so the host declaration is consumed by the
  provider block in the same unit, and the `variables` pin runs the corpus with no finding.
- No new CLI flag, and no change to the exit codes.
- The LF write path, the content rule (a file is written only when it has content), `check_variables` reading the
  whole `.tf` set as consumer text.
- `provider.tf` keeps `required_version = ">= 1.14"` and the pinned provider source and version, because
  `tests/conftest.py::declared_provider` reads the pinned version from a golden `provider.tf`.
- The generated README, `docs/USAGE_GUIDE.md`, `README.md` and `docs/MIGRATION_GUIDE.md` are migrated to the
  statement: the operator's `terraform.tfvars` holds the host, not a credential pair, and the key comes from the
  environment.
- `ruff check .` is clean, and `python3 -m pytest` passes. No test counts outside `agent-status.md`.

## Result

Met. The goldens moved only from a real run: 34 files, 22867 bytes to 24768 bytes (+1901). The statement, the
measurement and the pins above are what the committed code and documents now state, and `docs/README.md` names §11 as
the owner of the rule.

One finding is recorded in `backlog.md`, because the live `terraform validate` gate reports it on the kitchen sink
fixture and the pinned schema cannot state the constraint. The static rules report `PASS (0 FAIL, 1 WARN)` for the
same run, and the committed baseline reports the same validate finding, so the rule stated here did not cause it.
