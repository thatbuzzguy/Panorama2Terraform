# To-Do — current task: F4.1 Post-run sanity gate (Epic 4)

**Epic 3 is complete.** F3.10 (`docs/ARCHITECTURE.md`) is the last feature of
Epic 3 and is committed. Epic 4 is the next epic; F4.1 is its lowest-numbered
feature.

**Before writing code: overwrite `acceptance.md` with the F4.1 criteria.**

## Why this task

The static invariants F4.1 enforces exist today only as tests. They run when the
suite runs, not when a conversion runs, so a conversion that breaks an invariant
still writes files and exits 0. F4.1 makes the checks run on every conversion and
reports them.

## F4.1 sub-tasks

- [ ] Overwrite `acceptance.md` with the F4.1 criteria.
- [ ] A static check module (pure Python) that runs on every conversion and
      enforces: no dangling references, `location` on every resource, only
      `EMITTED_TYPES`, every emitted variable consumed (absorbs the F2.10
      `tests/test_variables.py` check), no raw control characters, and the
      expected placeholders (VPN pre-shared keys) as WARN not FAIL.
- [ ] `SANITY_REPORT.txt` plus a console summary; non-zero exit on FAIL.
- [ ] A `--validate` CLI flag that runs `terraform init` + `terraform validate`
      on the output.
- [ ] Share the rules with the existing tests instead of copying them: the
      no-dangling-reference rule already exists in
      `tests/test_dependency_wiring.py`, and the variable rule in
      `tests/test_variables.py`.
- [ ] Gates: ruff clean, pytest green, terraform validate green.

## Notes carried forward

- Determinism (two runs byte-identical) stays pinned by test, not paid in the CLI.
- `xml_input.py` is the only input read for both entry points; a new entry point
  must import `parse_xml`, not call `ET.parse(path)`.
- The naming rule, the location rule, the reference-resolution rule and the
  report grouping rule are stated once in `docs/ARCHITECTURE.md`; a new emitter
  must follow them and the doc must stay true.
- `location` is chosen from `LOCATION_SCHEMA`, never from the resource name.
  `terraform validate` accepts an unknown `location` sub-block and drops it
  silently, so the schema table is the authority, not validate.
- ElementTree `append` does not reparent: copy with `copy.deepcopy` when taking
  an element out of a tree another tree still uses.
- Reports are not in the golden set (`tests/golden/` holds `.tf` files only), so
  a report change does not move a golden; report determinism is pinned by
  `tests/test_reports.py::test_sections_and_entries_are_in_a_stable_order`.

## Deferred (tracked in backlog.md)

- **F4.2** — container table plus a line-tracking `TreeBuilder`; every unknown
  container reported. The container table in `docs/ARCHITECTURE.md` §3.1 is the
  seed.
- **F4.3** — per-entry `CONVERSION_REPORT.txt` (converted / report-only /
  unaccounted). It will surface the parsed-but-unaccounted gap recorded in
  `backlog.md` (regions reach no output today).
- **F4.4** — property-level coverage matrix extending `COVERAGE_MATRIX`.
