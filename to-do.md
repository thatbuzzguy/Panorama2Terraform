# To Do — F4.4 Property-level coverage (next feature)

F5.1 (source read boundary) is complete and committed. Its record is in the git
history. Acceptance criteria for F4.4 go into `acceptance.md` when the work starts.

Pieces:

1. [ ] Name the properties an emitter reads, per matrix row. `COVERAGE_MATRIX` is type
   level today; each row gains the property list the emitter uses.
2. [ ] Keep the two rules that already exist unchanged: the entry-mark rule and the
   section rule. A property level is a container inside a config-object entry, so
   `container_coverage` still reports only the section level.
3. [ ] Add the property scan and its report section: a property the parse captured but
   no output used is a gap. `entry_coverage` counts property entries on the parent row
   today; the scan reports them.
4. [ ] Change the two report lines that state the property scan as if it exists:
   `entry_coverage.summary_lines` prints "(F4.4 covers each one)", and the container
   coverage report prints "Field-level coverage is F4.3" for a property level.
5. [ ] Fix the two report defects found during the documentation refresh, in the same
   pass, because both change report output:
   - `parse_bgp` and `parse_ospf` read the same element through two paths, so a router
     under a device is read twice and printed twice. Keep one path, which is the rule
     in `docs/ARCHITECTURE.md` §3.4 that this pair breaks.
   - The BGP and OSPF manual report sections do not name their scope or the router.
     Apply the F3.9 scope rule to them.
6. [ ] Decide BGP `redist-rules`: print them, or stop capturing them.
7. [ ] Tests: the property scan, the parity between a matrix row and the properties its
   emitter reads, and the report section.
8. [ ] Documents: `docs/COVERAGE_MATRIX.md`, `docs/ARCHITECTURE.md` §2.4 and §3.1,
   `README.md`.
9. [ ] Gate: `ruff check .`, `pytest`, goldens byte-identical, report determinism tests,
   exit codes unchanged.

F5.4 and F5.6 wait on this feature, because a shadow and a drift are property-level
facts.

## Epic 5 pieces after F4.4

- F5.2 Cached API export: a producer that hands bytes to `parse_bytes`, a cache, and
  `--offline`. The tests use a fixture-backed producer, so no test calls the network.
  Decide the response wrapper shape before the container table covers a fetched scope.
- F5.3 Provenance record (`SOURCE.txt`) and the report label change.
- F5.5 Read-through data blocks (opt-in): `DATA_SOURCE_SCHEMA` verified against the
  provider `data_source_schemas`, plus the data-block gate rule.
