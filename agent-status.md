# Agent Status

## Current position

F4.4 (property-level coverage) is complete and committed. Gate at the commit:
`ruff check .` clean, `pytest` 642 passed, both golden sets byte-identical, report
determinism pinned by test, exit codes unchanged (a property finding is an operator
action, so it does not change the exit code).

The next feature is F5.2, the cached API export. Its pieces are in `to-do.md`.

F5.2 starts by deciding the response wrapper shape, because a fetched scope needs an
identity the report can name.

## What F4.4 changed

- `resource_mapping.COVERAGE_MATRIX`: each row gained `emitter` (the generator methods
  that read the row's properties) and `properties` (the keys those emitters read). The
  entry name and the four scope facts are the row identity, so they are not properties.
- `entry_coverage.py`: rule 4 (the property scan), `RecordingDict` (a captured object
  that records the keys an output reads from it), `start_recording()` so the record
  starts after the parse, `MATRIX_BY_RESOURCE`, `PROPERTY_HEADING`, `PROPERTY_RULE`,
  `property_findings()`, `property_line()`. `mark()` returns the recorded object, so a
  parse method must work through what it returns.
- `entry_coverage.EntryLedger.scope()` defect fixed: a scope name lives on the scope
  `<entry>`, not on the container, so the conversion report now prints the device-group,
  template and device sections.
- `panorama_to_terraform.py`: the property section in `generate_conversion_report` after
  the gap section, `main()` starts the read record before the first generator call, the
  console summary names the finding count.
- `parse_bgp` and `parse_ospf`: one path (`network/virtual-router/entry`), one record per
  enabled router, the four scope facts plus the router name. OSPF interface entries are
  now marked.
- The BGP and OSPF manual report sections name the scope and the router, print the
  peer-group nexthops and the redist rules. The capture decision is closed: what the
  parse captures is what the section prints.
- `container_coverage.py`: the stale report line for a property level, the ipsec crypto
  profile note.
- Tests: `tests/test_property_coverage.py` (the read record, parity with the matrix, the
  scan scope, the corpus findings, the report section), row-shape and grounding tests in
  `tests/test_coverage_matrix.py`, the mark rule and console pins in
  `tests/test_entry_coverage.py`, the BGP and OSPF parse shape in
  `tests/test_parse_network.py`, the router scope sections in `tests/test_reports.py`, and
  `run_pipeline` in `conftest.py` for a pipeline run inside the process.
- `tests/fixtures/router_scopes.xml`: two routers in two scopes, so a flat report cannot
  tell them apart.

## Facts measured during F4.4

- The corpus findings are the pinned set in `tests/test_property_coverage.py`. A property
  the parse captured and no output read, for a container a matrix row covers.
- Only `panos_address` names two emitters, because the manual setup report reads
  `declared_type`, `other` and `description` from a parsed object the `.tf` emitter does
  not read.
- One row has no corpus entry to measure: `panos_aggregate_layer3_subinterface`. The
  container table maps an aggregate subinterface to the ethernet subinterface row, so no
  entry reaches it.
- Field gaps in a container no row covers are measured and recorded in `backlog.md`:
  `report`, `inventory`, `bookkeeping`, `count-only` and `nested-block` containers.

## Rules to keep when writing documents

- One owner document per rule; every other document links to it.
- Machine-readable tables are code. A document explains a table and never restates it
  row by row, so a regenerated table cannot drift.
- No test counts in a document. A document names the test that pins a rule; the
  count lives in `agent-status.md` and the git history.
- A claim about what the tool does must name the module or the test that holds it. A
  feature id is written only when a module or a test uses it as a name.
- ASD-STE100 Simplified Technical English, no marketing voice, no emoji.
- A historical record (the audit report) keeps its findings and states the current
  state separately, so a reader does not take an old finding as a fact.

## Watch during F5.2

- The parse layer keeps the ElementTree tree, so a fetched scope must arrive as bytes and
  be parsed through `xml_input.parse_bytes`, never as a device-object model.
- The cache is the thing the report names, so a report line must be able to reopen the
  bytes it describes.
- The response wrapper shape decides whether a fetched scope can be named by the container
  table, which is what a report row keys on.
- `pan-os-python` is a lazy import in the fetch layer only. No test calls the network, so
  the producer in tests is fixture-backed.
- The property scan measures reads at run time, so a test that wants the read record must
  run the pipeline in process (`conftest.run_pipeline`), not through `run_script`.
