# Agent Status

## Current position

The documentation refresh is complete and committed as 068e3fd. Gate at the commit:
`ruff check .` clean, `pytest` 566 passed, both golden sets byte-identical,
`terraform validate` green on all four outputs, exit codes unchanged.

The next feature is F4.4, the property-level coverage matrix (`PLAN.md`). Its pieces
go into `to-do.md` when it starts. Two report defects found during this task land with
it: the overlapping BGP and OSPF read paths, and the manual report sections that do not
name their scope.

Epic 5 (upstream data sources) is now open, from the 2026-10-26 design conversation.
Three decisions came from it, and they are recorded in `PLAN.md` and `backlog.md`: the
first source is a cached Panorama API export; `pan-os-python` is allowed as a fetch
dependency with `xml_input.py` still standard library; references outside the run stay
plain strings, with read-through data blocks as an opt-in per declared scope.

One ordering decision is pending, so `to-do.md` is not written yet: F4.4 first, or F5.1
(first) with F4.4 second. F5.1 changes no behaviour, so it is safe in either order; F5.4
and F5.6 cannot start before F4.4.

## What this task changed

- Root markdown: `README.md`, `AGENTS.md`, `PLAN.md`, `backlog.md`,
  `ADVERSARIAL_AUDIT_REPORT.md` (status table), `acceptance.md`, `to-do.md`,
  `agent-status.md`.
- `docs/`: the index (`docs/README.md`) and every document in it.
  `docs/MULTI_VR_MIGRATION_GUIDE.md` and `docs/MULTI_VR_QUICK_ANSWER.md` were merged
  into `MIGRATION_GUIDE.md` and `DEVICE_GROUP_SPLITTING.md` and removed.
- In-code documentation: the generated `README.md` text in `generate_readme`, the CI
  workflow comment, `quick_start.sh`, `examples/example_interface_report.txt`, the
  module docstrings (`panorama_to_terraform.py`, `split_device_groups.py`,
  `container_coverage.py`, `entry_coverage.py`, `resource_mapping.py`), and
  `tests/test_golden_files.py` and `tests/test_container_coverage.py` docstrings.
- No code behaviour changed. No test expectation changed.

## Facts measured during this task

| Fact | Value |
|---|---|
| `EMITTED_TYPES` | 28 |
| `REPORT_ONLY_TYPES` | 10 |
| `NOT_EMITTED_TYPES` | 3 |
| `COVERAGE_MATRIX` rows | 28 |
| `LOCATION_SCHEMA` | 28 types |
| `INTERFACE_RESOURCE_TYPES` | 7 (virtual-wire and TAP are nested blocks, not types) |
| `DESTINATION_KINDS` | 8 |
| `CONTAINER_TABLE` rows | 68 |
| Gate checks | 7, in report order: `emitted_types`, `location_present`, `references`, `variables`, `control_chars`, `placeholders`, `terraform` |
| Report files | `CONVERSION_REPORT.txt`, `MANUAL_SETUP_REPORT.txt`, `INTERFACE_MIGRATION_REPORT.txt`, `VPN_MIGRATION_REPORT.txt`, written only when they have content; `SANITY_REPORT.txt` written on every run; plus `README.md` |
| Provider | `PaloAltoNetworks/panos` 2.0.14, 128 resource types, read from `terraform providers schema -json` |

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

## Rules to keep when writing documents

- One owner document per rule; every other document links to it.
- Machine-readable tables are code. A document explains a table and never restates it
  row by row, so a regenerated table cannot drift.
- No test counts in a document. Counts live here and in the git history.
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
