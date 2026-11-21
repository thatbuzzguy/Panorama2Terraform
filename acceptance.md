# Piece E10.3 acceptance criteria — a new site instantiated from an existing template

The decision this piece takes is what the tool can state offline for a template entry the export declares
and a device the export does not name. It is recorded in `docs/TEMPLATE_STACK_DEPLOYMENT.md` §4, which is
where the piece's decision lives. `docs/CODEBASE_ASSEMBLY.md` §3, §5, §8, §9 and §12 keep their rules and link
to that section; `PLAN.md` keeps the epic line. Pieces E10.1 and E10.2 are landed and are not reopened here.

Closed conditions:

1. The decision is grounded in the tool's own read on a fixture, not in speculation. The corpus holds no
   template entry that no device names, so the piece adds one fixture in `tests/fixtures/` that shows the
   shape: a device group that lists a template as a member and names no device, and a template entry with no
   device inside it. Every fact the decision states is read through the module that owns it —
   `entry_coverage.identity_of`, `unit_manifest.facts_of`, the manifest row, `site_data.build_rows`,
   `reference_edges.build_rows` and `order`, and the scope block emitter — on that fixture.
2. A fact only a live target states is not asserted and goes to `backlog.md`: the device the operator adds to
   the device group, and the serial a push target names. A fact the tool can state offline is not moved to the
   backlog.
3. The single-owner rule holds. The decision is stated once, in `docs/TEMPLATE_STACK_DEPLOYMENT.md` §4. The
   piece adds no second naming rule, no second reader, no second writer, no second console line, no environment
   name, and no field on the manifest row or on an edge row: the device fact is already one of the five scope
   facts, the site row already writes only for a value the run printed, and the membership pair is already read
   through `api_requests.LIST_JOIN`. If the measurement shows a module states a fact that the fixture cannot
   fill, the fix is in the owner module and the wording change is recorded with the decision.
4. Pins, one per fact the decision states, in the test module that owns the rule:
   - `tests/test_unit_manifest.py`: a manifest row for a template entry that no device names states the device
     fact as the empty fact, so the identity, the digest and the directory name are read from the four facts the
     export can name.
   - `tests/test_site_data.py`: a unit that names no device writes no site row and no `.tfvars` line, and its
     `provider.tf` states no `target`, so the site record holds no device value the run did not read.
   - `tests/test_reference_edges.py`: a device group that lists a template writes no edge row for that name,
     because the membership rule reads no device-group template list, so the relation stays the names printed
     inside the block.
   - `tests/test_scope_objects.py`: the scope block for such a template entry prints the entry name, the
     properties its row declares, and no device, and the device group block prints the template names as data.
    - `tests/test_commit_actions.py`: the commit and push rows for such a unit name the template fact, because the
      device fact is empty, so the action layer states no device value for it.
5. A fact more than one test module reads stays in `tests/conftest.py`, and no test module imports another test
   module. The new fixture is read by the corpus pins through `corpus_fixtures()`, so a pin that states the
   printed fixture set, a corpus edge count, or a corpus finding set is changed to the measured value in the
   same commit, and the fixture is not excluded from a corpus pin by name.
6. The gate runs single-threaded and reports measured counts: `ruff check .`, `ruff format --check .`,
   `python3 tools/check_documents.py`, `python3 -m pytest`. The pins run offline against fixtures; the pins that
   read the live provider schema skip for the missing `terraform` binary, and the same 4 skips are reported.
7. No document states a test count, and a document that names a test names a test that exists. Plain wording,
   no metaphor, no emoji. The `.tf` goldens are read as the bytes a run wrote, so a change that writes no `.tf`
   byte leaves the golden set unchanged.
8. `to-do.md` loses the completed piece, `agent-status.md` carries the position and the measurement, and
   `backlog.md` carries the live-only facts. The tracking markdown keeps no completed-piece narrative.
9. Two commits in the conventional-commits style, not pushed: one `feat(...)` or `fix(...)` commit for the rule
   and the pins, then one `docs(tracking)` commit carrying the decision and the measurement.
