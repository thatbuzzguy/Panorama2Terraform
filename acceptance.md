# Acceptance criteria — Piece 11C.2, the run's report section

Piece 11C.2 of Epic 11, the codebase several runs write into
(`docs/MULTI_RUN_CODEBASE.md`). This is the whole task: Piece 11C.3 (the
write boundary) is not started here.

Owner documents: `docs/MULTI_RUN_CODEBASE.md` §7 (the report section rule)
and §8 (the module owners). Owner modules: `entry_coverage.py` for the report
rule, `unit_manifest.py` for the two sets, `codebase_state.py` for the join
that reads the merged site rows. Pin module: `tests/test_reports.py`.

## Definition of done

1. The section prints after the report sections the report rule already
   orders (header, summary, gaps, property findings, shadows, repeated names,
   reference cycles, state ownership, drift) and follows the same shape the
   other report sections use: the `--- heading ---` line, the rule paragraph,
   then the grouped body.
2. The section names the run's unit set and the codebase's unit set, read
   through `unit_manifest.units`, the one unit rule, so no module states a
   second unit set and no gate rule states a unit rule of its own.
3. A unit is named by its name, the deepest scope the export declares, read
   through `unit_manifest.unit_name` and `unit_manifest.facts_of`; the report
   names no directory and no path.
4. The body is grouped by the F3.9 scope rule
   (`TerraformGenerator._report_scope_path` and `_report_section_header`), so
   no module states a second grouping rule.
5. The section prints only when the codebase set holds a unit the run set
   does not. A run that reads the whole codebase prints no such section, so
   its report bytes are unchanged and no committed golden report moves.
6. Report content only: no console line. The console line shape has one owner,
   `container_coverage.console_line`.
7. The site-record finding #2 is closed: `unit_manifest.units` reads a row set
   through `facts_of`, so a site row (fields `directory`, `variables`, no
   facts) names no unit, and the rule that reads the merged site rows is
   `codebase_state.py`'s join key on `directory` plus the data rule. The report
   states no site row field.

## Pins to write (tests/test_reports.py, plus one in test_codebase_state.py)

- The section prints for a run that does not read the whole codebase, and its
  unit lines name the units through `unit_manifest.units` for the committed
  pair (`tests/fixtures/kitchen_sink.xml` then `tests/fixtures/address_objects.xml`).
- The section does not print for a run that reads the whole codebase, and the
  report bytes of a whole-codebase run are unchanged.
- The section prints after the sections the report rule already orders.
- The section names no directory: no line in it matches a unit directory name.
- The report gains no console line: the section text is not in the console
  output.
- Site-row pin: every merged site row's `directory` is `unit_manifest.directory_name`
  for a unit the merged manifest names, so the site half names the same units
  through the join and adds none.

Pins measure content and names, not document wording. No test module imports
another test module; shared facts come from `tests/conftest.py`
(`CODEBASE_FIXTURE`, `RUN_FIXTURE`, `record_rows`, `partial_run`). No
hand-built rows.

## Gate

`ruff check .`, `ruff format --check .`, `python3 -m pytest`,
`python3 tools/check_documents.py`; single-threaded and conservative.
