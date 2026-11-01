# Acceptance criteria — F6.8: the gate rule that reads the data files

Feature record: `PLAN.md` Epic 6. The rule is `sanity_checks.check_data_files`, the sixth gate rule
for a file set. The four data files are `CODEBASE_MANIFEST.json` (F6.1), `OWNERSHIP.json` (F6.2),
`REFERENCE_EDGES.json` (F6.3), and `SITE_DATA.json` (F6.6); the rule also reads `site.auto.tfvars`
as the printed form of the site record. The tests are `tests/test_data_file_gate.py`, the four
rewritten file-set tests in `tests/test_unit_manifest.py`, `tests/test_ownership.py`,
`tests/test_reference_edges.py` and `tests/test_site_data.py`, and the new negative test in
`tests/test_sanity_gate.py`.

## Decisions

### 1. The gate reads the data files, and the file-set statement changes

The gate reads `.tf` files plus the four data files. `site.auto.tfvars` is the printed form of the
site record, so the rule reads it through the record and does not count it as a data file.
`SANITY_REPORT.txt` names the data-file count, and the console summary names both sets. The file-set
statement in `docs/ARCHITECTURE.md` §4.5, the `.tfvars` statement in §4.5, the check table in §4.6,
and the tests that pinned the file set change together (the `agent-status.md` watch rule).

`CHECK_ORDER` gains `data_files` after `variables`: the block rules, then the run-level text rules,
then the data rule, then the byte rules. The position is pinned by the rewritten edge test.

### 2. The rule reads each row through the module that owns the row shape

The rule calls `parse_rows` on each data file that is present, so no second shape rule appears. The
rule reports a refusal as a finding, because the gate reads the files the operator receives: a data
file a person hand-wrote is an input, and the gate cannot assume the writer used the module. A data
file that reads as no rows is a finding, because the content rule says the tool writes the file only
when it has content, so a data file cannot be empty. The rule does not crash on a file that is not
readable JSON; it reports it.

### 3. The findings, each a FAIL

The rule states one fact: the data files must agree with the rules that produced them and with each
other. Six findings:

1. A data file that does not read as its declared rows, or a data file with no rows.
2. A row field that `naming.py` decides must be stated as the rule states it: the manifest `unit`
   and `directory`, and the ownership `directory`, each read through `unit_manifest`.
3. A join: every `directory` a data file names must name a unit the manifest names, or a row of
   `OWNERSHIP.json` itself — the declared parent source names no manifest unit (F5.4). An edge row
   must join on (`type`, `entry`) to an ownership row whose `owner` names the `target`. A row whose
   `kind` is `ambiguous` states no owner, so a `kind` with no owner cannot name one.
4. An order: the manifest `rank` and `after` must be what `reference_edges.order` produces from the
   three records read back, so `after` names only units the manifest names.
5. A printed form: `site.auto.tfvars` must equal `site_data.render_tfvars` of the site rows, and the
   two files stand or fall together on the content rule.
6. The position of a data-file finding is its row ordinal in the declared order, because a data row
   spans many lines in the file. A file-level finding states no line.

### 4. The order graph reads only manifest units (a bug fix the rule forces)

`reference_edges.py` rule 7 states that the order graph reads only the units the manifest names, but
the inheritance rule in `dependencies` was not guarded, so an override row whose owner is a
parent-source unit put a directory the manifest does not name into `after`, and the rule could not
read the order back. Measured: `order` returned `rank` 0 and `after = [parent]` for that row. Fix:
guard the inheritance rule with the node set, the way the edge rule is guarded. Pinned by
`tests/test_reference_edges.py::test_a_declared_parent_source_adds_no_dependency`, extended with the
override row.

### 5. The reports and the exit code

No report names the data files or restates a row, so the four "no report names a field" tests are
unchanged, and the rule reports a violation on the file, not a restated row. The exit code rule is
unchanged: the F4.1 gate decides it, a data-file FAIL exits 1. A WARN is not a data-file finding.

### 6. Truth across the corpus

The rule reports no finding on the files the tool itself writes, for every fixture, because the tool
writes the data through the same rules the rule reads. The committed goldens are unchanged, the gate
reports no finding on them, and two runs on the same source write the same bytes and report the same
findings.

## Acceptance criteria

1. `tests/test_data_file_gate.py` pins the file-set rule, the shape refusal, the content rule, the
   naming agreement, the joins, the order read-back, the printed form, the row-ordinal position, the
   `CHECK_ORDER` position, the corpus truth, and the determinism, including one negative test per
   finding.
2. `tests/test_sanity_gate.py` gains the negative test for the rule (the "each check detects its own
   violation" pin), the report-shape pin for the data-file count, and the console-summary pin for the
   new line shape.
3. The tests that pinned the file set name the rule through their own module, and
   `tests/test_reference_edges.py` pins the order-graph guard.
4. `sanity_checks.py` states the rule once, imports the four data modules, and reads nothing else;
   `check_data_files` takes the output directory, not the `.tf` file set, so no block rule reads a
   data file and no data rule reads a `.tf` file.
5. `docs/ARCHITECTURE.md` §4.5 and §4.6, `docs/CODEBASE_ASSEMBLY.md` §7 rule 1, §5 rule 4, §6 rule
   7, and §9 rule 6, the docstrings of `sanity_checks.py`, `site_data.py`, `reference_edges.py`,
   `ownership.py` and `unit_manifest.py`, the `main()` comment in `panorama_to_terraform.py`, the
   `README.md` and `docs/USAGE_GUIDE.md` gate sections, and the `agent-status.md` watch rule state
   the landed rule and name the test that holds it.
6. `ruff check .` is clean, `pytest` is green, the gate reports no finding on the goldens, and the
   change is committed. The tracking markdown loses the F6.8 detail, and `PLAN.md` keeps the open
   Epic 6 half: the write path.

## Results

All criteria are met. Measured: the sample run writes 10 `.tf` files and 2 data files, and the console
line reads `Sanity gate: PASS (0 FAIL, 0 WARN) - 10 .tf files, 2 data files, 20 resources`.
`reference_cycle.xml` and `kitchen_sink.xml` each write 4 data files; `scope_child.xml` writes none, so
the corpus test does not assert a count above 0. `ruff check .` is clean, `pytest` is green (1238),
and the rule reports no finding on every fixture and on both golden sets.
