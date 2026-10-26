# To Do — Documentation Refresh (complete)

Acceptance criteria and the result are in `acceptance.md`.

- [x] Read every markdown file in the repository and check each claim against the code.
- [x] Overwrite `acceptance.md` with the criteria for this task.
- [x] Measure the current facts: `pytest`, `ruff`, the mapping counts, the report
  formats, the CLI flags, the CI job.
- [x] `README.md`: claims, documentation index, testing section without counts.
- [x] `docs/README.md`: one index that names each document and its reader task.
- [x] `docs/ARCHITECTURE.md`: module table, §2.4 destinations, §3.1 the open path
  exception, §4.5 report files, §7 the claims that are now implemented.
- [x] `docs/USAGE_GUIDE.md`: rewrite the stale feature, output, troubleshooting and
  version sections; add the quick start script.
- [x] `docs/MIGRATION_GUIDE.md`: merge `docs/MULTI_VR_MIGRATION_GUIDE.md` into it;
  fix the "what gets converted" list. `docs/MULTI_VR_MIGRATION_GUIDE.md` removed.
- [x] `docs/DEVICE_GROUP_SPLITTING.md`: merge `docs/MULTI_VR_QUICK_ANSWER.md` into
  it; fix the split-output tree and the shared-object claim.
  `docs/MULTI_VR_QUICK_ANSWER.md` removed.
- [x] `docs/COVERAGE_MATRIX.md`: regenerate the table from `COVERAGE_MATRIX` (28 rows).
- [x] `docs/RESOURCE_MAPPING.md`: correct the bucket counts, add the interface kinds,
  state the nested-block rule, verify each claim against the live provider schema.
- [x] `docs/ADVANCED-ROUTING-ENGINE-SUPPORT.md`: correct the parsed/not-parsed wording,
  confirm the example against the golden file.
- [x] `docs/VPN_ROUTING_CONFIG_EXAMPLES.md`: correct the generated-file claims and the
  XML shapes the parser reads.
- [x] `docs/DUAL-LICENSING-EXPLAINED.md`: trim to the factual license summary.
- [x] In-code documentation: the generated output `README.md` text, the CI workflow
  comment, the `test_golden_files.py` docstring, `quick_start.sh`, `examples/`, and the
  module and test docstrings.
- [x] `AGENTS.md`: state that `lib_docs/` is not in the repo.
- [x] `ADVERSARIAL_AUDIT_REPORT.md`: add the status table so a point-in-time finding
  is not read as a current fact.
- [x] Add to `backlog.md` the gaps the documents confirmed: the overlapping BGP and
  OSPF paths, the manual report sections that do not name their scope, BGP
  redistribution captured but not printed, the two report lines that name F4.4, and
  `lib_docs/` missing.
- [x] Update `PLAN.md`, `agent-status.md`, then commit.
- [x] Gate: `ruff check .`, `pytest`, goldens byte-identical, `terraform validate`,
  exit codes unchanged.

## Next feature — F4.4 property-level coverage

Pieces go here when the work starts. The two report output lines that name F4.4 change
with it (`backlog.md`), and the two report defects found during this task are fixed in
the same pass (`PLAN.md` sequencing).
