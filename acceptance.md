# Acceptance — a value the provider constrains in code, not in the schema

## Measurement

Measured 2026-11-04 against provider 2.0.14 with Terraform v1.16.2, on a real kitchen-sink run read through
`sanity_checks.run_checks` with `run_terraform=True`:

- The static rules report `PASS (0 FAIL, 1 WARN)`. The one WARN is the VPN key placeholder in `vpn.tf`.
- The `terraform` check reports one FAIL, on the unit `shared_45ca31c3`: `Invalid Attribute Value Match` —
  `disable_override value must be one of: ["no"], got: "yes"` for `panos_administrative_tag.env_prod_5301b734`.
  `terraform providers schema -json` states no value list for that field, so the constraint is in the provider
  code, and `tests/conftest.py::provider_schemas` cannot answer it offline.
- A plan reads only the files in the directory it runs on. On the kitchen run, `terraform validate` at the
  codebase root answers "The configuration is valid" with no configuration files, because the `.tf` files sit
  inside the unit directories. So `tests/test_terraform_validate.py::test_terraform_validate_kitchen_succeeds`
  passes without reading the generated config. That is the part of Goal 2 this slice fixes.

## The rule (one statement, stated once)

Owner: `docs/ARCHITECTURE.md` §4.6, the gate.

The gate is a static gate: it reads the files it wrote against the tables it can read offline. A value
constraint the provider carries in its code, not in the schema JSON, is not data the gate can read, so it
cannot become a gate rule and the FAIL rule does not change. The emitter prints the value the export states,
and the `terraform` check is the rule that reports such a value as FAIL when the run uses `--validate`, so the
report is the operator's notice. A fixture that a validate pin reads is test data, so it states the value the
provider accepts, and the plan check reads what the run wrote: one plan per unit directory the record names.

Rejected candidate: a verified-value table read by the gate at check time, with a WARN in the placeholder
style. The fact would be a table the gate can only verify by running the provider, not by reading the schema,
so the static gate would depend on a live binary to decide a rule, and a WARN rule would need a value list the
pinned schema does not state. It also restates a fact the tool cannot read offline.

## What the code must do

1. `tests/fixtures/kitchen_sink.xml` states `no` for `disable-override` on the shared `env-prod` tag entry, so
   the kitchen validate pin passes. The goldens change only from a real run.
2. `tests/fixtures/tags.xml` keeps `yes`: it is the F4.4 flag-read pin, no validate pin reads it, and the
   F4.4 pins read that fixture (`tests/test_parse_objects.py::FLAG_READS`, `tests/test_ownership.py::SEVEN_ROWS`).
3. `tests/test_terraform_validate.py` runs each fixture plan through the same function the CLI calls on
   `--validate`, once per unit directory the record names, so each pin reads the files the run wrote. Every
   fixture in the file writes one directory per unit, so the rule applies to the whole file, not only the
   kitchen case: a pin that validates at the codebase root reads no configuration file. The
   skipped-when-absent rule is unchanged, and the tooling gate (the provider resolves and installs) is still
   pinned inside a unit directory the run wrote.
4. `tests/test_sanity_gate.py` pins the gate for the kitchen run with `terraform` available: `PASS (0 FAIL,
   1 WARN)`, the WARN is the placeholder, and every `terraform` result is PASS, one result per unit directory.
5. `docs/ARCHITECTURE.md` §4.6 states the rule once and names the two tests. The provider fact itself stays
   recorded in `backlog.md`, as a fact the tool cannot read, and links to §4.6 for the rule.

## Pins

1. `tests/test_terraform_validate.py::test_terraform_validate_kitchen_succeeds` — skipped when the binary is
   absent; asserts PASS for every unit directory the record names.
2. `tests/test_sanity_gate.py::test_kitchen_sink_gate_passes_with_validate` — skipped when the binary is
   absent; asserts `Result: PASS (0 FAIL, 1 WARN)`, the placeholder WARN, and one PASS `terraform` result per
   unit directory.
3. `tests/test_golden_files.py` pins the golden bytes unchanged except `tests/golden/kitchen_sink/shared_45ca31c3/tags.tf`,
   regenerated from a real run; the golden file set does not change.
4. `tests/test_build_kitchen_sink.py` keeps its data counts: the comment count and the entry-name counts do not move.

## Rules this must keep

- FAIL, WARN, SKIPPED and exit codes are unchanged, and `CHECK_ORDER` does not change.
- No new table, and no second statement of a value held elsewhere.
- The single block reader, the report determinism, and the report counts are unchanged.
- `ruff check .` is clean, and `python3 -m pytest` passes. No test counts outside `agent-status.md`.

## Result

Met, 2026-11-04.

- `tests/fixtures/kitchen_sink.xml` states the value the provider accepts for the shared `env-prod` entry, and
  `tests/golden/kitchen_sink/shared_45ca31c3/tags.tf` changed from a real run: the address golden and the golden
  file set are unchanged.
- `tests/test_terraform_validate.py` runs the plan once per unit directory the record names, for every fixture in
  the file, so each pin reads the files the run wrote instead of passing at a root that holds no configuration file.
- `tests/test_sanity_gate.py::test_kitchen_sink_gate_passes_with_validate` reads the report the run wrote and reports
  `Result: PASS (0 FAIL, 1 WARN)`: the one WARN is the placeholder in `shared_a6577c11/vpn.tf`, and every plan result
  is PASS, one per unit directory.
- `docs/ARCHITECTURE.md` §4.6 states the rule once and names both tests, and `backlog.md` keeps the provider fact as
  a fact the tool cannot read offline.
- `ruff check .` is clean and `python3 -m pytest` passes.
