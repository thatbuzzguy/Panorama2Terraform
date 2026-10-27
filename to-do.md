# To Do — F5.3 Provenance Record (next feature)

Epic 5 in progress. F5.1 (the read door) and F5.2 (the cached API export) landed; their
records are in the git history. F5.3 is next, because a run now needs to say which source it
read.

Acceptance criteria for F5.3 go into `acceptance.md` when the work starts.

Pieces:

1. [ ] Decide what the provenance record states: the source kind, the file path or the host
   and request identity, the cache entry the run read, and the scope. One record per run,
   naming bytes a reader can reopen.
2. [ ] `SOURCE.txt` is written outside the report bodies, so the report byte rule still holds.
   Decide which files the goldens cover, and how a determinism test handles a name that comes
   from the cache.
3. [ ] The report label change from `Input file:` to `Source:`, which F5.1 left as it was. The
   golden sets pin the report bytes, so the label change regenerates them; state that in the
   acceptance criteria before the code.
4. [ ] The cache pruning rule: an entry is not pruned while a report references it. The rule
   needs the reference to be data, not a printed line.
5. [ ] Gate: `ruff check .`, `pytest`, goldens byte-identical after the label change, report
   determinism, exit codes unchanged.
6. [ ] Documents: `docs/ARCHITECTURE.md` §3 and §6, `docs/USAGE_GUIDE.md` (the output file
   list), `README.md`.

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
- The per-scope API fetch (`type=config&action=get&path=...`) is refused today because a
  `result` with no `config` element is not the shape the container table knows. F5.4 owns it.
- F5.5 Read-through data blocks (opt-in): `DATA_SOURCE_SCHEMA` verified against the
  provider `data_source_schemas`, plus the data-block gate rule.
