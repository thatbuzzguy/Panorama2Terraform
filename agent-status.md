# Agent Status

## Current position

F5.1 (source read boundary) is complete and committed as 737d607. Gate at the commit:
`ruff check .` clean, `pytest` 572 passed, both golden sets byte-identical,
`terraform validate` green on all four outputs, exit codes unchanged, and the kitchen-sink
output byte-identical against the same run at eab4f54.

The next feature is F4.4, the property-level coverage matrix, with the two report defects
that land in the same pass. Its pieces are in `to-do.md`.

Order decision (2026-10-26): F5.1 first, then F4.4. F5.1 changed no behaviour, so it is
safe in either order; F5.4 and F5.6 wait on F4.4.

Epic 5 (upstream data sources) is open. Three decisions came from the 2026-10-26
conversation, recorded in `PLAN.md` and `backlog.md`:

- the first source the tool uses is a cached Panorama API export,
- `pan-os-python` is allowed as a fetch dependency, with `xml_input.py` still standard
  library and a lazy import,
- a name outside the run stays a plain string; read-through data blocks are opt-in per
  declared scope.

## What F5.1 changed

- `xml_input.py`: `SourceOrigin` (kind, name, path), `parse_bytes(data, origin,
  max_input_bytes)` as the producer boundary, `parse_xml(path)` as the file producer, and
  refusals that name the origin.
- `tests/test_safe_input.py`: six tests for the boundary. No existing expectation changed.
- `docs/ARCHITECTURE.md` §1 and §3, `README.md` Safe input.
- No report output changed. The `Source:` label is recorded for F5.3.

## Facts measured on 2026-10-26 (provider data sources)

| Fact | Value |
|---|---|
| `data_source_schemas` in panos 2.0.14 | 128, mirroring the 128 `resource_schemas` |
| Emitted types with a data-source counterpart | all 28 |
| Types whose data-source schema equals the resource schema (attributes and `location` sub-blocks) | 126 of 128 |
| Resource-only names | `panos_certificate_import`, `panos_virtual_router_interface` |
| Data-source-only names | `panos_certificate`, `panos_predefined_dlp_file_type` |
| `required_attributes` on a data source | none, so `terraform validate` cannot enforce `name` + `location` |
| Data source that returns a collection | `panos_addresses` (map keyed by name) |
| Membership data sources | `panos_device_group` (devices + vsys, templates), `panos_template_stack` (devices, templates), `panos_template` (default_vsys) |

Run counts are recorded here and in the git history, not in documents.

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

## Watch during F4.4

- The entry-mark rule is an AST check over parse methods and their helper calls, so a
  method that reads entries through a variable path is accepted only when it marks
  somewhere in the call chain (`tests/test_entry_coverage.py::_reads_entries`).
- The report line shape is pinned field by field in `entry_coverage.entry_line`.
- Two report lines already name F4.4 as if it exists; they change when the scan lands.
- The table parity test matches a row path by segment presence, not by full path order,
  because a method can reach a container through a helper. Narrowing that to full-path
  comparison needs the pattern list to be data, not string literals inside methods.
