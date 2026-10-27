# To Do — F5.4 Cross-Source Shadow Report (next feature)

Epic 5 in progress. F5.1 (the read door), F5.2 (the cached API export) and F5.3 (the
provenance record) landed; their records are in the git history. F5.4 is next, because the
record now names the scope a source holds, and a shadow is the fact a single source cannot
show.

Acceptance criteria for F5.4 go into `acceptance.md` when the work starts.

Pieces:

1. [ ] Decide the per-scope response rule. A `result` with no `config` element is the
   per-scope shape (`type=config&action=get&path=...`), which the wrapper decision refuses
   today because it is not the whole-config shape the container table knows. F5.4 owns a rule
   for it, and the rule must keep the origin and the line map as the same objects.
2. [ ] Decide what a shadow is at property level: a child entry name that repeats a parent
   name. A per-device-group run cannot see its parent, so an inherited name stays a plain
   string and a shadowed object is invisible (the property scan, F4.4).
3. [ ] Decide which property scan rule reports a shadow, and where it prints: the property
   section of `CONVERSION_REPORT.txt` is the section that names a matrix row, so a shadow is
   a finding there or it needs its own section decided first.
4. [ ] The ledger names the source of each entry. The provenance record is the data for that,
   so a shadow row names both sources by the bytes each one read.
5. [ ] The parent as a second source, read offline: one cache entry per request identity, so a
   shadow test runs with no network and CI still passes.
6. [ ] Gate: `ruff check .`, `pytest`, goldens byte-identical, report determinism, exit codes
   unchanged.
7. [ ] Documents: `docs/ARCHITECTURE.md` §3.3 and §4.5, `docs/COVERAGE_MATRIX.md`,
   `docs/USAGE_GUIDE.md`, `README.md`.

## Open items that are not in this feature

- The prune action. The rule is in `provenance.py` (F5.3), and the reference is data, but no
  command runs the prune. Recorded in `backlog.md`.
- Property gaps in a container no matrix row covers (report, inventory, bookkeeping,
  count-only, nested-block): recorded in `backlog.md`, and pinned as out of scope by
  `tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers`.
- The console prints the gap lines only; printing property findings needs the console
  line shape decided first.
- `panos_aggregate_layer3_subinterface` has no corpus entry to measure, so its declared
  properties are grounded in the emitter source only.
- F5.5 Read-through data blocks (opt-in): `DATA_SOURCE_SCHEMA` verified against the
  provider `data_source_schemas`, plus the data-block gate rule.
- F5.6 Terraform state as a source: report-only ownership and drift, offline, using the
  property scan.
