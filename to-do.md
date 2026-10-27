# To Do — F5.2 Cached API export (next feature)

Epic 4 is complete. F4.4 (property-level coverage) landed with the two report defects
that belonged to it; its record is in the git history.

Acceptance criteria for F5.2 go into `acceptance.md` when the work starts.

Pieces:

1. [ ] Decide the response wrapper shape before the container table covers a fetched
   scope. A fetched scope needs an identity the report can name, so the wrapper shape is
   the first decision, not the last.
2. [ ] `source_fetch.py` as a byte producer only: it hands bytes to
   `xml_input.parse_bytes` with a `SourceOrigin`. The parse layer keeps the ElementTree
   tree, because the container table, the entry ledger, the parent walk and the line map
   are keyed on the tree.
3. [ ] The cache: the cache entry is what gets parsed, so a report line still names bytes
   a reader can reopen.
4. [ ] `--offline` reads the cache only, so a run with no network passes CI.
5. [ ] `pan-os-python` is the only place a dependency exists, imported lazily.
   `xml_input.py` stays standard library.
6. [ ] Tests use a fixture-backed producer, so no test calls the network.
7. [ ] Gate: `ruff check .`, `pytest`, goldens byte-identical, report determinism,
   exit codes unchanged.
8. [ ] Documents: `docs/ARCHITECTURE.md` §1 and §3, `README.md`.

F5.4 and F5.6 use the property scan F4.4 landed, because a shadow and a drift are
property-level facts.

## Open items that are not in this feature

- Property gaps in a container no matrix row covers (report, inventory, bookkeeping,
  count-only, nested-block): recorded in `backlog.md`, and pinned as out of scope by
  `tests/test_property_coverage.py::test_scan_scope_is_the_entries_a_matrix_row_covers`.
- The console prints the gap lines only; printing property findings needs the console
  line shape decided first.
- `panos_aggregate_layer3_subinterface` has no corpus entry to measure, so its declared
  properties are grounded in the emitter source only.
- F5.3 Provenance record (`SOURCE.txt`) and the report label change.
- F5.5 Read-through data blocks (opt-in): `DATA_SOURCE_SCHEMA` verified against the
  provider `data_source_schemas`, plus the data-block gate rule.
