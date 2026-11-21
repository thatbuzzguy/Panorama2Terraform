# Piece E10.2 acceptance criteria — the scope a template entry and a stack entry are declared inside

The decision this piece takes is what `resource_mapping.SCOPE_PLACEMENT` answers for a `panos_template`
entry and a `panos_template_stack` entry, and whether `unit_manifest` needs a field for that fact. It is
recorded in `docs/TEMPLATE_STACK_DEPLOYMENT.md` §3, which is where the piece's decision lives. Piece E10.3
and the `backlog.md` items are not started here.

Closed conditions:

1. The decision is grounded in the pinned provider data and in a fixture, not in speculation: the answer is
   read from `resource_mapping.LOCATION_SCHEMA`, and the export shape is measured on
   `tests/fixtures/scope_objects.xml` through the tool's own read (`identity_of`, `facts_of`). A fact the tool
   cannot read offline goes to `backlog.md` and is not asserted.
2. The single-owner rule holds. `SCOPE_PLACEMENT` and the location sub-block are one fact, so the piece adds
   no second naming rule, no second reader, and no restated table: `SCOPE_PLACEMENT` keeps its empty set for
   the two template-chain rows, `unit_manifest` gains no field, and `docs/CODEBASE_ASSEMBLY.md` §3 rule 2 and
   `docs/ARCHITECTURE.md` §2.2 lose the wording that states a template can sit inside a stack, because the
   measurement shows the export cannot hold that shape. The decision is stated once, in
   `docs/TEMPLATE_STACK_DEPLOYMENT.md` §3, and the other documents link to it.
3. The decision as measured: a template entry and a stack entry name no container, so the placement read
   answers no containing scope, the location prints the empty sub-block, and the naming context is empty. The
   row already states placement through the five fact keys, so no field is needed; for these two units the
   container fact key holds the parse fallback, which is not a fact value. The relation the export states
   between a device group or a stack and a template is a membership list, read through
   `api_requests.membership_lists` and joined through `api_requests.LIST_JOIN`, so Piece E10.1's edge set is
   the only place that relation is stated.
4. Pins, one per fact the decision states:
   - `tests/test_scope_objects.py`: a placement key names a sub-block that can hold a scope name, so a row
     whose only sub-block declares no `name` states no placement key, and the two template-chain rows read
     that way.
   - `tests/test_scope_objects.py`: the parse records no container fact for a template entry and for a stack
     entry on the fixture, so the placement read answers no containing scope.
   - `tests/test_unit_manifest.py`: the row states placement through the fact keys it already reads, so
     `FIELD_ORDER` holds no field for it; the two measured rows state the entry's own name and no container.
   - `tests/test_unit_manifest.py`: the level order is read through `named_fact` on the shapes the export can
     hold, so the pin that read a template inside a stack measures the stack row alone.
5. The gate runs single-threaded and reports measured counts: `ruff check .`, `ruff format --check .`,
   `python3 tools/check_documents.py`, `python3 -m pytest`. The pins run offline against fixtures; the pins
   that read the live provider schema skip for the missing `terraform` binary, and the same 4 skips are
   reported. A test module imports no other test module, so a fact more than one test module reads stays in
   `tests/conftest.py`.
6. No document states a test count, and a document that names a test names a test that exists. Plain
   wording, no metaphor, no emoji.
7. `to-do.md` loses the completed piece, `agent-status.md` carries the position and the measurement, and
   `backlog.md` changes only if a live-only fact appears. The tracking markdown keeps no completed-piece
   narrative.
8. Two commits in the conventional-commits style, not pushed: one `feat(...)` or `fix(...)` commit for the
   rule wording and the pins, then one `docs(tracking)` commit carrying the decision and the measurement.
