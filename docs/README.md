# Documentation Index

Each rule in this project lives in one document. The other documents link to
that document instead of restating the rule.

| Document | What it is for |
|---|---|
| [USAGE_GUIDE.md](USAGE_GUIDE.md) | Run each script, and read each output file |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Why the output looks the way it does. Each rule names the test that pins it |
| [RESOURCE_MAPPING.md](RESOURCE_MAPPING.md) | The provider v2 decision for each type, with the reason |
| [COVERAGE_MATRIX.md](COVERAGE_MATRIX.md) | Which XML element feeds which resource, and the test that proves it |
| [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) | Plan and run a migration, for one device or several virtual routers |
| [CODEBASE_ASSEMBLY.md](CODEBASE_ASSEMBLY.md) | What a full codebase needs, and what the converter does not do yet. Design only, Epic 6 |
| [DEVICE_GROUP_SPLITTING.md](DEVICE_GROUP_SPLITTING.md) | Split one export into one file per device group |
| [ADVANCED-ROUTING-ENGINE-SUPPORT.md](ADVANCED-ROUTING-ENGINE-SUPPORT.md) | Logical routers, and the routing config the converter does not read |
| [VPN_ROUTING_CONFIG_EXAMPLES.md](VPN_ROUTING_CONFIG_EXAMPLES.md) | The XML shapes the parser reads for VPN and routing |
| [DUAL-LICENSING-EXPLAINED.md](DUAL-LICENSING-EXPLAINED.md) | The two license options |

## Who owns each rule

| Rule | Owner |
|---|---|
| Identity, the five scope facts, parsed object shape | `ARCHITECTURE.md` §2 |
| Safe input read, container table, entry marks | `ARCHITECTURE.md` §3 |
| Per-scope source shape, the envelope rule, the scope path shape | `ARCHITECTURE.md` §3.1, and `container_coverage.py` |
| Cross-source shadow scan (the fact, the line shape, the heading) | `ARCHITECTURE.md` §3.2, and `shadow_coverage.py` |
| The destination one entry takes (the one place that answers it, and the order) | `ARCHITECTURE.md` §3.2, and `entry_coverage.py` (`EntryLedger.destination`) |
| Emit order, location, reference resolution, policy chains, reports, gate | `ARCHITECTURE.md` §4 |
| The round-trip cross-check (the block set against the entry set, per unit and row) | `ARCHITECTURE.md` §4.6, and `sanity_checks.check_round_trip`, which reads the scan scope through `entry_coverage.matrix_row_for` |
| The protocol object shape, the one-of mapping, and what prints | `ARCHITECTURE.md` §4.9, and `resource_mapping.PROTOCOL_SHAPE` |
| The filter container shape, the row scope, and the path-keyed input spellings | `ARCHITECTURE.md` §4.10, and `resource_mapping.FILTER_SHAPE` |
| The certificate container shape, the choice by presence, and the `sensitive` print | `ARCHITECTURE.md` §4.11, and `resource_mapping.CERTIFICATE_SHAPE` |
| Local resource naming | `ARCHITECTURE.md` §5 |
| Determinism | `ARCHITECTURE.md` §6 |
| Provider type per object kind | `RESOURCE_MAPPING.md`, and `resource_mapping.py` |
| Provider element per emitted type | `COVERAGE_MATRIX.md`, and `resource_mapping.COVERAGE_MATRIX` |
| Migration workflow | `MIGRATION_GUIDE.md` |
| Device group to template join | `DEVICE_GROUP_SPLITTING.md` |
| Codebase unit, ownership, order between units, import blocks, scope objects, site data, commit action, the write path | `CODEBASE_ASSEMBLY.md` §3 to §11 and §14, and the modules `unit_manifest.py`, `ownership.py`, `reference_edges.py`, `import_blocks.py`, `site_data.py`, `commit_actions.py`, `write_path.py` |
| The credential rule, stated once | `CODEBASE_ASSEMBLY.md` §11 is the owner; `ARCHITECTURE.md` §3 links to it and keeps only what the fetch layer enforces, and `README.md`, `docs/USAGE_GUIDE.md` and `docs/MIGRATION_GUIDE.md` link to it |
| Provenance record, the cache reference, and the prune action it gates | `ARCHITECTURE.md` §3.3, and `provenance.py`; the two file sets the record belongs to are `CODEBASE_ASSEMBLY.md` §14 |
| Repository layout: the directories, the import rule, the flat test rule | `ARCHITECTURE.md` §1.1, `AGENTS.md` (the tracking set), and the four readme indexes (`README.md`, this file, `../examples/README.md`, `../tools/README.md`) |
| The fixture assembler: its read rule, its merge rule, and the rule that the committed fixture is the record it does not write | `ARCHITECTURE.md` §1.1, `../tools/README.md`, and `tests/test_build_kitchen_sink.py` |

The machine-readable tables are code, not documents:
[`../src/resource_mapping.py`](../src/resource_mapping.py),
[`../src/container_coverage.py`](../src/container_coverage.py), and the entry marks in
[`../src/entry_coverage.py`](../src/entry_coverage.py). A document explains a table and
never restates it row by row.
