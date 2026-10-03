# Agent Status

## Current position
Epic 1 (testing and linting foundation) is COMPLETE. Next: **Epic 2, F2.1 Provider baseline** (see `to-do.md`).

## Session log

### F1.7 — Security and robustness (this session)
- Added `tests/test_robustness.py` (10 tests, all green) plus six fixtures
  under `tests/fixtures/`: hostile_billion_laughs, hostile_xxe,
  hostile_bad_control_char (raw 0x01 byte), robust_tab_cr_names
  (names carry `&#9;`/`&#13;` char refs that survive attribute
  normalization), robust_empty_names, robust_name_collisions.
- Found: ElementTree resolves internal DTD entities, so a deep entity
  chain is a memory DoS. Fix (in both scripts): reject any input
  containing `<!DOCTYPE` before parsing. Panorama exports never carry a
  DTD, so this is safe.
- Fix: `escape_string` now escapes `\t` and `\r` and strips remaining C0
  control characters and DEL, so generated .tf files never carry raw
  control bytes (invalid HCL).
- Fix: sanitization collisions. `a-b`, `a_b`, `A-B` all sanitized to
  `a_b`, emitting duplicate resource addresses (invalid HCL). New
  `TerraformGenerator.unique_resource_name(name, scope)` registry assigns
  per-type collision-free names (`a_b`, `a_b_2`, `a_b_3`) and is stable
  for repeated input, so cross-resource references (which recompute the
  same input string) resolve to the same name. Migrated all 34 call
  sites with per-resource-type scopes.
- Fix: `main()` catches `ValueError` (DTD rejection) with a clean message.
  Hostile input now exits non-zero with no traceback.
- Goldens byte-identical (no collisions in sample/kitchen-sink).
- Gate: ruff clean. pytest 106 passed, 46 xfailed, 13 xpassed.

### Epic 1 summary (complete; detail in git history)
- F1.1/F1.8 tooling + lint gate (ruff, pytest, CI matrix, pre-commit).
- F1.2 parser unit tests: 42 tests, 34 fixtures; 5 parser bugs fixed.
- F1.3 golden-file tests: sample + kitchen-sink (29 .tf), 39 tests.
- F1.4 schema conformance: 56 cases; 43 xfailed (13 types missing from
  provider v2, missing `location`), 13 xpassed.
- F1.5 CI terraform gate: init green, validate xfail until Epic 2.
- F1.6 edge corpus: 6 fixtures, 12 tests; splitter quote bug fixed.

## Environment notes
- Python 3.12.3; use `uvx --with pytest==9.1.1 pytest` and
  `uvx --with ruff==0.16.10 ruff` (PEP 668 blocks system pip installs).
- terraform 1.16.1 available at /usr/bin/terraform.
- Converter CLI: `python3 panorama_to_terraform.py <input.xml> [--output-dir DIR]`
  (output dir is a flag, default `terraform_output`).
- Splitter CLI: `python3 split_device_groups.py <input.xml> [--output-dir DIR]`.
- Provider v2 schema (128 types) was fetched to /tmp/panos_schema.json in a
  previous session; refetch with `terraform providers schema -json` if needed.
- 13 emitted types are missing from v2 (F2.2 mapping targets); `location`
  is a required string attribute (not a block).

## Conventions
- One task at a time; `acceptance.md` overwritten before each task.
- ASD-STE100 in commits and docs.
- Red→green: failing checks are xfail(strict=False) with the fixing
  Epic's task reference; flip them to plain asserts when the epic lands.
- Commit per feature; completed items leave markdown when the epic completes.
